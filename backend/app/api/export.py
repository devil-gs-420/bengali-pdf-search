"""
Export API Routes: Generate and download CSV, Excel, JSON exports.
"""

import logging
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import ExportRequest
from app.services.export_service import generate_export

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/export")
async def export_records(
    export_request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export voter records in CSV, Excel, or JSON format.
    
    - **format**: csv | excel | json
    - **query**: Optional text filter
    - **filters**: Optional field filters
    - **fields**: Specific fields to include (None = all fields)
    - **max_records**: Maximum records to export (up to 100,000)
    """
    result = await generate_export(db, export_request)

    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "X-Record-Count": str(result["record_count"]),
        },
    )
