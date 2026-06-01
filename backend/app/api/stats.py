"""
Statistics API Routes: Dashboard data and system analytics.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Document, DocumentStatus, SearchHistory, UploadLog, VoterRecord, User
from app.schemas.schemas import SystemStatsResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats", response_model=SystemStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return comprehensive system statistics for the dashboard."""

    # Document counts by status
    status_counts = {}
    for status in DocumentStatus:
        result = await db.execute(
            select(func.count(Document.id)).where(Document.status == status)
        )
        status_counts[status.value] = result.scalar() or 0

    # Total voter records
    total_records_result = await db.execute(select(func.count(VoterRecord.id)))
    total_records = total_records_result.scalar() or 0

    # Total searches
    total_searches_result = await db.execute(select(func.count(SearchHistory.id)))
    total_searches = total_searches_result.scalar() or 0

    # Recent uploads (last 24 hours)
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_result = await db.execute(
        select(func.count(Document.id)).where(Document.created_at >= yesterday)
    )
    recent_uploads = recent_result.scalar() or 0

    # Storage used (sum of file sizes)
    storage_result = await db.execute(select(func.sum(Document.file_size)))
    storage_bytes = storage_result.scalar() or 0
    storage_mb = round(storage_bytes / (1024 * 1024), 2)

    # Top districts by record count
    top_districts_result = await db.execute(
        select(VoterRecord.district, func.count(VoterRecord.id).label("count"))
        .where(VoterRecord.district.isnot(None))
        .group_by(VoterRecord.district)
        .order_by(desc("count"))
        .limit(10)
    )
    top_districts = [
        {"district": row[0], "count": row[1]}
        for row in top_districts_result.all()
    ]

    # Recent activity (last 10 upload sessions)
    recent_logs_result = await db.execute(
        select(UploadLog)
        .order_by(UploadLog.started_at.desc())
        .limit(10)
    )
    recent_logs = recent_logs_result.scalars().all()
    recent_activity = [
        {
            "session_id": log.session_id,
            "folder_name": log.folder_name,
            "total_files": log.total_files,
            "processed_files": log.processed_files,
            "total_records": log.total_records,
            "status": log.status,
            "started_at": log.started_at.isoformat() if log.started_at else None,
        }
        for log in recent_logs
    ]

    return SystemStatsResponse(
        total_documents=sum(status_counts.values()),
        total_records=total_records,
        failed_documents=status_counts.get("failed", 0),
        processing_documents=status_counts.get("processing", 0),
        pending_documents=status_counts.get("pending", 0),
        completed_documents=status_counts.get("completed", 0),
        total_searches=total_searches,
        recent_uploads=recent_uploads,
        storage_used_mb=storage_mb,
        top_districts=top_districts,
        recent_activity=recent_activity,
    )
