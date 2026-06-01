"""
ORM Models: All database tables for the Bengali PDF Search System.
Each model maps to a database table via SQLAlchemy ORM.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Index, Integer, String, Text, JSON,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UploadStatus(str, enum.Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


# ─── User Model ───────────────────────────────────────────────────────────────

class User(Base):
    """Authenticated system users with role-based access control."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    documents = relationship("Document", back_populates="uploaded_by_user", lazy="select")
    upload_logs = relationship("UploadLog", back_populates="user", lazy="select")
    search_history = relationship("SearchHistory", back_populates="user", lazy="select")

    def __repr__(self):
        return f"<User {self.email} role={self.role}>"


# ─── Document Model ───────────────────────────────────────────────────────────

class Document(Base):
    """
    Represents a single uploaded PDF file.
    Tracks processing status, metadata, and extracted record counts.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)            # Original filename
    stored_path = Column(String(1000), nullable=False)         # Path on disk
    file_size = Column(Integer, nullable=True)                 # Bytes
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 for deduplication
    page_count = Column(Integer, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    is_scanned = Column(Boolean, default=False, nullable=False)  # True if OCR was used
    ocr_confidence = Column(Float, nullable=True)                # Average OCR confidence
    records_extracted = Column(Integer, default=0, nullable=False)
    processing_time_seconds = Column(Float, nullable=True)
    folder_path = Column(String(1000), nullable=True)           # Original folder structure
    upload_log_id = Column(Integer, ForeignKey("upload_logs.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    voter_records = relationship("VoterRecord", back_populates="document", cascade="all, delete-orphan", lazy="select")
    upload_log = relationship("UploadLog", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_documents_status_created", "status", "created_at"),
        Index("ix_documents_filename", "filename"),
    )

    def __repr__(self):
        return f"<Document {self.filename} status={self.status}>"


# ─── VoterRecord Model ────────────────────────────────────────────────────────

class VoterRecord(Base):
    """
    Extracted structured data from a Bengali voter ID / voter list PDF.
    Each row represents one voter's information extracted from a PDF page.
    Full-text search indexes are added for efficient searching.
    """
    __tablename__ = "voter_records"

    id = Column(Integer, primary_key=True, index=True)

    # ── Core voter fields ──────────────────────────────────────────
    voter_id = Column(String(50), nullable=True, index=True)          # ভোটার নম্বর
    serial_number = Column(String(20), nullable=True)                  # ক্রমিক নম্বর
    name = Column(String(300), nullable=True, index=True)             # নাম
    name_english = Column(String(300), nullable=True)                  # English name if available
    father_name = Column(String(300), nullable=True, index=True)      # পিতার নাম
    mother_name = Column(String(300), nullable=True, index=True)      # মাতার নাম
    spouse_name = Column(String(300), nullable=True)                   # স্বামী/স্ত্রীর নাম
    birth_date = Column(String(50), nullable=True)                     # জন্মতারিখ (kept as string to handle Bengali formats)
    birth_year = Column(Integer, nullable=True, index=True)           # Extracted year for range queries
    gender = Column(String(20), nullable=True)                         # লিঙ্গ
    occupation = Column(String(200), nullable=True)                    # পেশা

    # ── Address fields ─────────────────────────────────────────────
    address = Column(Text, nullable=True)                              # Full address
    village = Column(String(300), nullable=True, index=True)          # গ্রাম
    post_office = Column(String(200), nullable=True)                   # ডাকঘর
    union_name = Column(String(200), nullable=True, index=True)       # ইউনিয়ন
    ward = Column(String(50), nullable=True, index=True)              # ওয়ার্ড
    upazila = Column(String(200), nullable=True, index=True)          # উপজেলা
    district = Column(String(200), nullable=True, index=True)         # জেলা
    division = Column(String(100), nullable=True)                      # বিভাগ

    # ── Source tracking ────────────────────────────────────────────
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=True)                       # PDF page number
    raw_text = Column(Text, nullable=True)                             # Original extracted text for debugging
    extraction_confidence = Column(Float, nullable=True)               # OCR/extraction confidence score
    extra_fields = Column(JSON, nullable=True)                         # Any additional extracted fields

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    document = relationship("Document", back_populates="voter_records")

    # Indexes for search performance
    __table_args__ = (
        Index("ix_voter_records_name_father", "name", "father_name"),
        Index("ix_voter_records_district_upazila", "district", "upazila"),
        Index("ix_voter_records_union_ward", "union_name", "ward"),
    )

    def __repr__(self):
        return f"<VoterRecord {self.name} voter_id={self.voter_id}>"


# ─── UploadLog Model ──────────────────────────────────────────────────────────

class UploadLog(Base):
    """
    Tracks each folder upload session.
    Aggregates stats for all PDFs processed in a single upload operation.
    """
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)  # UUID
    folder_name = Column(String(500), nullable=True)
    total_files = Column(Integer, default=0, nullable=False)
    processed_files = Column(Integer, default=0, nullable=False)
    failed_files = Column(Integer, default=0, nullable=False)
    total_records = Column(Integer, default=0, nullable=False)
    status = Column(Enum(UploadStatus), default=UploadStatus.started, nullable=False)
    error_details = Column(JSON, nullable=True)  # List of error messages
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="upload_logs")
    documents = relationship("Document", back_populates="upload_log")

    def __repr__(self):
        return f"<UploadLog {self.session_id} status={self.status}>"


# ─── SearchHistory Model ──────────────────────────────────────────────────────

class SearchHistory(Base):
    """
    Records search queries for analytics, suggestions, and audit trails.
    """
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False, index=True)
    filters = Column(JSON, nullable=True)        # Applied filters as JSON
    results_count = Column(Integer, default=0)
    search_duration_ms = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    # Relationship
    user = relationship("User", back_populates="search_history")

    def __repr__(self):
        return f"<SearchHistory query='{self.query}' results={self.results_count}>"
