"""
Documents API Routes: Upload PDFs (single or folder), list documents, trigger processing.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import (
    DocumentListResponse, DocumentResponse,
    UploadProgressResponse, UploadSessionResponse,
)
from app.services.document_service import (
    check_duplicate, create_document_record, create_upload_session,
    get_documents, get_upload_session, process_document_async,
    update_upload_progress,
)
from app.services.pdf_processor import compute_file_hash

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Upload Single or Multiple PDFs ──────────────────────────────────────────

@router.post("/upload", response_model=UploadSessionResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folder_name: Optional[str] = Form(default="upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload one or more PDF files for processing.
    Files are saved to disk and processed asynchronously in the background.
    Returns a session_id to track progress.
    
    - Validates file type (PDF only)
    - Checks file size limit
    - Detects duplicates by SHA-256 hash
    - Spawns background processing tasks
    """
    # Validate files
    valid_files = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            logger.warning(f"Skipped non-PDF: {f.filename}")
            continue
        valid_files.append(f)

    if not valid_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF files provided",
        )

    # Create upload session
    upload_log = await create_upload_session(
        db,
        folder_name=folder_name or "upload",
        total_files=len(valid_files),
        user_id=current_user.id,
    )

    # Save files and queue processing
    async def _process_files():
        """Background task: save files, check duplicates, process each PDF."""
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as bg_db:
            for upload_file in valid_files:
                try:
                    # Read file content
                    content = await upload_file.read()

                    # Check file size
                    if len(content) > settings.max_upload_bytes:
                        logger.warning(f"File too large: {upload_file.filename}")
                        await update_upload_progress(
                            bg_db, upload_log.session_id, failed_delta=1
                        )
                        continue

                    # Save to uploads directory
                    upload_dir = settings.upload_path / upload_log.session_id
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    file_path = upload_dir / upload_file.filename
                    file_path.write_bytes(content)

                    # Compute hash for duplicate detection
                    file_hash = compute_file_hash(str(file_path))
                    duplicate = await check_duplicate(bg_db, file_hash)

                    if duplicate:
                        logger.info(f"Duplicate detected: {upload_file.filename}")
                        # Still record but mark as duplicate
                        doc = await create_document_record(
                            bg_db,
                            filename=upload_file.filename,
                            stored_path=str(file_path),
                            file_size=len(content),
                            file_hash=file_hash,
                            upload_log_id=upload_log.id,
                            folder_path=folder_name,
                            user_id=current_user.id,
                        )
                        await update_upload_progress(
                            bg_db, upload_log.session_id, processed_delta=1
                        )
                        continue

                    # Create document record
                    doc = await create_document_record(
                        bg_db,
                        filename=upload_file.filename,
                        stored_path=str(file_path),
                        file_size=len(content),
                        file_hash=file_hash,
                        upload_log_id=upload_log.id,
                        folder_path=folder_name,
                        user_id=current_user.id,
                    )

                    # Process the PDF (extract text and voter records)
                    await process_document_async(
                        bg_db, doc.id, str(file_path), upload_log.session_id
                    )

                except Exception as e:
                    logger.error(f"Error processing {upload_file.filename}: {e}", exc_info=True)
                    await update_upload_progress(bg_db, upload_log.session_id, failed_delta=1)

            # Mark session as completed
            from sqlalchemy import update
            from app.db.models import UploadLog, UploadStatus
            from datetime import datetime, timezone
            await bg_db.execute(
                update(UploadLog)
                .where(UploadLog.session_id == upload_log.session_id)
                .values(
                    status=UploadStatus.completed,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await bg_db.commit()
            logger.info(f"Upload session {upload_log.session_id} completed")

    background_tasks.add_task(_process_files)

    return UploadSessionResponse(
        session_id=upload_log.session_id,
        total_files=len(valid_files),
        status="started",
        message=f"Processing {len(valid_files)} PDF(s) in the background",
    )


# ─── Upload Progress ──────────────────────────────────────────────────────────

@router.get("/upload/{session_id}/progress", response_model=UploadProgressResponse)
async def get_upload_progress(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll upload/processing progress for a given session_id."""
    log = await get_upload_session(db, session_id)
    if not log:
        raise HTTPException(status_code=404, detail="Upload session not found")

    progress = (
        (log.processed_files + log.failed_files) / log.total_files * 100
        if log.total_files > 0 else 0.0
    )

    return UploadProgressResponse(
        session_id=log.session_id,
        total_files=log.total_files,
        processed_files=log.processed_files,
        failed_files=log.failed_files,
        total_records=log.total_records,
        status=log.status,
        progress_percent=round(progress, 1),
        error_details=log.error_details,
    )


# ─── List Documents ───────────────────────────────────────────────────────────

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all uploaded documents with pagination and optional status filter."""
    result = await get_documents(db, page=page, page_size=page_size, status=status)
    return DocumentListResponse(**result)


# ─── Get Single Document ──────────────────────────────────────────────────────

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details for a single document."""
    from sqlalchemy import select
    from app.db.models import Document

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ─── Reprocess Document ───────────────────────────────────────────────────────

@router.post("/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-trigger processing for a failed document."""
    from sqlalchemy import select, delete
    from app.db.models import Document, VoterRecord

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete existing voter records first
    await db.execute(delete(VoterRecord).where(VoterRecord.document_id == document_id))
    await db.commit()

    async def _reprocess():
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            await process_document_async(bg_db, document_id, doc.stored_path)

    background_tasks.add_task(_reprocess)
    return {"message": f"Reprocessing document {document_id}", "status": "started"}


# ─── Delete Document ──────────────────────────────────────────────────────────

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and all its associated voter records."""
    from sqlalchemy import select, delete
    from app.db.models import Document, VoterRecord
    from app.core.security import require_admin

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    try:
        Path(doc.stored_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Could not delete file {doc.stored_path}: {e}")

    await db.execute(delete(VoterRecord).where(VoterRecord.document_id == document_id))
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
