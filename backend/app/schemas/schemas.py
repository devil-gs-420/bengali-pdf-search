"""
Pydantic Schemas: Request validation and response serialization for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores and hyphens allowed)")
        return v.lower()


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Document Schemas ─────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: Optional[int]
    page_count: Optional[int]
    status: str
    error_message: Optional[str]
    is_scanned: bool
    ocr_confidence: Optional[float]
    records_extracted: int
    processing_time_seconds: Optional[float]
    folder_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─── VoterRecord Schemas ──────────────────────────────────────────────────────

class VoterRecordResponse(BaseModel):
    id: int
    voter_id: Optional[str]
    serial_number: Optional[str]
    name: Optional[str]
    name_english: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    spouse_name: Optional[str]
    birth_date: Optional[str]
    birth_year: Optional[int]
    gender: Optional[str]
    occupation: Optional[str]
    address: Optional[str]
    village: Optional[str]
    post_office: Optional[str]
    union_name: Optional[str]
    ward: Optional[str]
    upazila: Optional[str]
    district: Optional[str]
    division: Optional[str]
    document_id: int
    page_number: Optional[int]
    extraction_confidence: Optional[float]
    pdf_file_name: Optional[str] = None  # Computed from document

    model_config = {"from_attributes": True}


class VoterRecordListResponse(BaseModel):
    items: List[VoterRecordResponse]
    total: int
    page: int
    page_size: int
    pages: int
    query: Optional[str]
    search_duration_ms: Optional[float]


# ─── Search Schemas ───────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: Optional[str] = None                # General text search
    name: Optional[str] = None                 # Name field filter
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    voter_id: Optional[str] = None
    birth_date: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    union_name: Optional[str] = None
    ward: Optional[str] = None
    occupation: Optional[str] = None
    village: Optional[str] = None
    gender: Optional[str] = None
    birth_year_from: Optional[int] = None
    birth_year_to: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "id"
    sort_order: str = "asc"


# ─── Upload Schemas ───────────────────────────────────────────────────────────

class UploadSessionResponse(BaseModel):
    session_id: str
    total_files: int
    status: str
    message: str


class UploadProgressResponse(BaseModel):
    session_id: str
    total_files: int
    processed_files: int
    failed_files: int
    total_records: int
    status: str
    progress_percent: float
    error_details: Optional[List[str]] = None


# ─── Stats Schemas ────────────────────────────────────────────────────────────

class SystemStatsResponse(BaseModel):
    total_documents: int
    total_records: int
    failed_documents: int
    processing_documents: int
    pending_documents: int
    completed_documents: int
    total_searches: int
    recent_uploads: int        # Last 24h
    storage_used_mb: float
    top_districts: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]


# ─── Export Schemas ───────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = Field(default="csv", pattern="^(csv|excel|json)$")
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    fields: Optional[List[str]] = None   # Which fields to export (None = all)
    max_records: int = Field(default=10000, le=100000)
