"""
Document Service: Orchestrates PDF processing, database persistence, and upload session management.
Uses ThreadPoolExecutor for concurrent PDF processing without blocking the async event loop.
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Document, DocumentStatus, UploadLog, UploadStatus, VoterRecord
from app.services.pdf_processor import compute_file_hash, process_pdf

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound PDF processing
_thread_pool = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)


# ─── Upload Session Management ────────────────────────────────────────────────

async def create_upload_session(
    db: AsyncSession,
    folder_name: str,
    total_files: int,
    user_id: Optional[int] = None,
) -> UploadLog:
    """Create a new upload session log entry."""
    session_id = str(uuid.uuid4())
    log = UploadLog(
        session_id=session_id,
        folder_name=folder_name,
        total_files=total_files,
        status=UploadStatus.started,
        user_id=user_id,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    logger.info(f"Created upload session {session_id} for {total_files} files")
    return log


async def get_upload_session(db: AsyncSession, session_id: str) -> Optional[UploadLog]:
    """Retrieve an upload session by its UUID."""
    result = await db.execute(
        select(UploadLog).where(UploadLog.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def update_upload_progress(
    db: AsyncSession,
    session_id: str,
    processed_delta: int = 0,
    failed_delta: int = 0,
    records_delta: int = 0,
):
    """Atomically update upload session counters."""
    await db.execute(
        update(UploadLog)
        .where(UploadLog.session_id == session_id)
        .values(
            processed_files=UploadLog.processed_files + processed_delta,
            failed_files=UploadLog.failed_files + failed_delta,
            total_records=UploadLog.total_records + records_delta,
        )
    )
    await db.commit()


# ─── Document Management ──────────────────────────────────────────────────────

async def create_document_record(
    db: AsyncSession,
    filename: str,
    stored_path: str,
    file_size: int,
    file_hash: str,
    upload_log_id: Optional[int] = None,
    folder_path: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Document:
    """Create a Document record in the database."""
    doc = Document(
        filename=filename,
        stored_path=stored_path,
        file_size=file_size,
        file_hash=file_hash,
        status=DocumentStatus.pending,
        upload_log_id=upload_log_id,
        folder_path=folder_path,
        uploaded_by=user_id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def check_duplicate(db: AsyncSession, file_hash: str) -> Optional[Document]:
    """Check if a PDF with the same SHA-256 hash already exists."""
    result = await db.execute(
        select(Document)
        .where(Document.file_hash == file_hash)
        .where(Document.status == DocumentStatus.completed)
    )
    return result.scalar_one_or_none()


async def save_voter_records(
    db: AsyncSession,
    document_id: int,
    records: List[Dict],
) -> int:
    """
    Bulk-insert extracted voter records for a document.
    
    Returns:
        Number of records inserted.
    """
    if not records:
        return 0

    voter_records = []
    for rec in records:
        # Convert birth_year string to int if present
        birth_year_raw = rec.get("birth_year")
        birth_year = None
        if birth_year_raw:
            try:
                birth_year = int(birth_year_raw)
            except (ValueError, TypeError):
                pass

        vr = VoterRecord(
            document_id=document_id,
            voter_id=rec.get("voter_id"),
            serial_number=rec.get("serial_number"),
            name=rec.get("name"),
            father_name=rec.get("father_name"),
            mother_name=rec.get("mother_name"),
            spouse_name=rec.get("spouse_name"),
            birth_date=rec.get("birth_date"),
            birth_year=birth_year,
            gender=rec.get("gender"),
            occupation=rec.get("occupation"),
            address=rec.get("address"),
            village=rec.get("village"),
            post_office=rec.get("post_office"),
            union_name=rec.get("union_name"),
            ward=rec.get("ward"),
            upazila=rec.get("upazila"),
            district=rec.get("district"),
            division=rec.get("division"),
            page_number=rec.get("page_number"),
            raw_text=rec.get("raw_text"),
            extraction_confidence=rec.get("extraction_confidence"),
        )
        voter_records.append(vr)

    db.add_all(voter_records)
    await db.commit()
    return len(voter_records)


# ─── Core Processing Pipeline ─────────────────────────────────────────────────

async def process_document_async(
    db: AsyncSession,
    document_id: int,
    pdf_path: str,
    session_id: Optional[str] = None,
) -> int:
    """
    Process a single PDF document asynchronously.
    Runs CPU-bound PDF processing in a thread pool to avoid blocking the event loop.
    
    Returns:
        Number of records extracted.
    """
    import asyncio

    # Mark as processing
    await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(status=DocumentStatus.processing, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()

    try:
        # Run blocking PDF processing in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_thread_pool, process_pdf, pdf_path)

        if result["error"]:
            raise RuntimeError(result["error"])

        # Compute extraction confidence per record
        from app.services.text_extractor import calculate_extraction_confidence
        for rec in result["records"]:
            rec["extraction_confidence"] = calculate_extraction_confidence(rec)

        # Save records to database
        records_count = await save_voter_records(db, document_id, result["records"])

        # Update document with results
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=DocumentStatus.completed,
                page_count=result["page_count"],
                is_scanned=result["is_scanned"],
                ocr_confidence=result["ocr_confidence"],
                records_extracted=records_count,
                processing_time_seconds=result["processing_time_seconds"],
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

        # Update upload session progress
        if session_id:
            await update_upload_progress(
                db, session_id,
                processed_delta=1,
                records_delta=records_count,
            )

        logger.info(f"Document {document_id} processed: {records_count} records")
        return records_count

    except Exception as e:
        error_msg = str(e)[:500]
        logger.error(f"Failed to process document {document_id}: {error_msg}", exc_info=True)

        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=DocumentStatus.failed,
                error_message=error_msg,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

        if session_id:
            await update_upload_progress(db, session_id, failed_delta=1)

        return 0


# ─── Document Queries ─────────────────────────────────────────────────────────

async def get_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> Dict:
    """Paginated list of documents."""
    query = select(Document)
    count_query = select(func.count(Document.id))

    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    query = query.order_by(Document.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    count_result = await db.execute(count_query)

    items = result.scalars().all()
    total = count_result.scalar()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
