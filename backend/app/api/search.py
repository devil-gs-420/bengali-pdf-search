"""
Search API Routes: Full-text and multi-field search for voter records.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import SearchRequest, VoterRecordListResponse
from app.services.search_service import (
    get_distinct_values, get_search_suggestions, search_voter_records
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search", response_model=VoterRecordListResponse)
async def search(
    # General text search
    q: Optional[str] = Query(default=None, description="General search query"),
    # Field-specific filters
    name: Optional[str] = Query(default=None),
    father_name: Optional[str] = Query(default=None),
    mother_name: Optional[str] = Query(default=None),
    voter_id: Optional[str] = Query(default=None),
    birth_date: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    upazila: Optional[str] = Query(default=None),
    union_name: Optional[str] = Query(default=None),
    ward: Optional[str] = Query(default=None),
    occupation: Optional[str] = Query(default=None),
    village: Optional[str] = Query(default=None),
    gender: Optional[str] = Query(default=None),
    birth_year_from: Optional[int] = Query(default=None),
    birth_year_to: Optional[int] = Query(default=None),
    # Pagination
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search voter records with multi-field filtering.
    
    - **q**: Search across name, father_name, voter_id, address simultaneously
    - Individual field parameters for precise filtering
    - Supports partial matching (substring search)
    - Bengali Unicode fully supported
    - Paginated results
    """
    search_request = SearchRequest(
        query=q,
        name=name,
        father_name=father_name,
        mother_name=mother_name,
        voter_id=voter_id,
        birth_date=birth_date,
        district=district,
        upazila=upazila,
        union_name=union_name,
        ward=ward,
        occupation=occupation,
        village=village,
        gender=gender,
        birth_year_from=birth_year_from,
        birth_year_to=birth_year_to,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await search_voter_records(db, search_request, user_id=current_user.id)
    return VoterRecordListResponse(**result)


@router.post("/search", response_model=VoterRecordListResponse)
async def search_post(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search using POST body — useful for complex filter combinations."""
    result = await search_voter_records(db, search_request, user_id=current_user.id)
    return VoterRecordListResponse(**result)


@router.get("/search/suggestions")
async def get_suggestions(
    q: str = Query(min_length=1),
    field: str = Query(default="name", pattern="^(name|district|upazila|union_name|occupation)$"),
    limit: int = Query(default=10, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get autocomplete suggestions for search fields (Bengali + English)."""
    suggestions = await get_search_suggestions(db, query=q, field=field, limit=limit)
    return {"suggestions": suggestions}


@router.get("/search/filters")
async def get_filter_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all distinct values for filter dropdowns (districts, upazilas, etc.)."""
    districts = await get_distinct_values(db, "district")
    divisions = await get_distinct_values(db, "division")
    genders = await get_distinct_values(db, "gender")

    return {
        "districts": districts,
        "divisions": divisions,
        "genders": genders,
    }
