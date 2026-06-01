"""
Search Service: Bengali-aware full-text and multi-field search engine.
Supports partial matching, multi-field filtering, and search history recording.
Optimized for both SQLite (development) and PostgreSQL (production).
"""

import logging
import time
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, VoterRecord, SearchHistory
from app.schemas.schemas import SearchRequest

logger = logging.getLogger(__name__)


# ─── Unicode Normalization ────────────────────────────────────────────────────

def normalize_search_query(query: str) -> str:
    """
    Normalize a search query for consistent matching.
    - Unicode NFC normalization
    - Strip extra whitespace
    - Lowercase (for English fields)
    """
    if not query:
        return ""
    normalized = unicodedata.normalize("NFC", query.strip())
    return normalized


def build_like_pattern(value: str) -> str:
    """Build a SQL LIKE pattern for partial matching (case-insensitive prefix/suffix)."""
    # Escape SQL LIKE special characters
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# ─── Core Search Function ─────────────────────────────────────────────────────

async def search_voter_records(
    db: AsyncSession,
    search: SearchRequest,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute a multi-field search against voter records.
    
    Features:
    - General query searches name, father_name, mother_name, voter_id, address simultaneously
    - Individual field filters apply exact/partial matching
    - Results joined with document data (filename)
    - Paginated
    - Search duration tracked
    
    Returns:
        dict with items, total, page, page_size, pages, query, search_duration_ms
    """
    start = time.time()

    # ── Build query ───────────────────────────────────────────────
    stmt = (
        select(VoterRecord, Document.filename.label("pdf_filename"))
        .join(Document, VoterRecord.document_id == Document.id)
        .where(Document.status == "completed")
    )

    conditions = []

    # General text search: search across multiple key fields simultaneously
    if search.query:
        q = normalize_search_query(search.query)
        pattern = build_like_pattern(q)
        general_conditions = or_(
            VoterRecord.name.ilike(pattern),
            VoterRecord.father_name.ilike(pattern),
            VoterRecord.mother_name.ilike(pattern),
            VoterRecord.voter_id.ilike(pattern),
            VoterRecord.address.ilike(pattern),
            VoterRecord.village.ilike(pattern),
            VoterRecord.occupation.ilike(pattern),
            VoterRecord.spouse_name.ilike(pattern),
        )
        conditions.append(general_conditions)

    # Individual field filters
    field_map = {
        "name": VoterRecord.name,
        "father_name": VoterRecord.father_name,
        "mother_name": VoterRecord.mother_name,
        "voter_id": VoterRecord.voter_id,
        "birth_date": VoterRecord.birth_date,
        "district": VoterRecord.district,
        "upazila": VoterRecord.upazila,
        "union_name": VoterRecord.union_name,
        "ward": VoterRecord.ward,
        "occupation": VoterRecord.occupation,
        "village": VoterRecord.village,
        "gender": VoterRecord.gender,
    }

    for field_name, column in field_map.items():
        value = getattr(search, field_name, None)
        if value:
            normalized = normalize_search_query(value)
            # voter_id and ward: exact or prefix match; others: partial
            if field_name in ("voter_id", "ward"):
                conditions.append(column.ilike(f"{normalized}%"))
            else:
                conditions.append(column.ilike(build_like_pattern(normalized)))

    # Birth year range filter
    if search.birth_year_from:
        conditions.append(VoterRecord.birth_year >= search.birth_year_from)
    if search.birth_year_to:
        conditions.append(VoterRecord.birth_year <= search.birth_year_to)

    # Apply all conditions
    if conditions:
        stmt = stmt.where(and_(*conditions))

    # ── Count total results ───────────────────────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # ── Sorting ───────────────────────────────────────────────────
    sort_column_map = {
        "id": VoterRecord.id,
        "name": VoterRecord.name,
        "voter_id": VoterRecord.voter_id,
        "district": VoterRecord.district,
        "created_at": VoterRecord.created_at,
    }
    sort_col = sort_column_map.get(search.sort_by, VoterRecord.id)
    if search.sort_order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    # ── Pagination ────────────────────────────────────────────────
    offset = (search.page - 1) * search.page_size
    stmt = stmt.offset(offset).limit(search.page_size)

    # ── Execute ───────────────────────────────────────────────────
    result = await db.execute(stmt)
    rows = result.all()

    # ── Build response items ──────────────────────────────────────
    items = []
    for row in rows:
        record = row[0]  # VoterRecord instance
        filename = row[1]  # pdf_filename label

        item = {
            "id": record.id,
            "voter_id": record.voter_id,
            "serial_number": record.serial_number,
            "name": record.name,
            "name_english": record.name_english,
            "father_name": record.father_name,
            "mother_name": record.mother_name,
            "spouse_name": record.spouse_name,
            "birth_date": record.birth_date,
            "birth_year": record.birth_year,
            "gender": record.gender,
            "occupation": record.occupation,
            "address": record.address,
            "village": record.village,
            "post_office": record.post_office,
            "union_name": record.union_name,
            "ward": record.ward,
            "upazila": record.upazila,
            "district": record.district,
            "division": record.division,
            "document_id": record.document_id,
            "page_number": record.page_number,
            "extraction_confidence": record.extraction_confidence,
            "pdf_file_name": filename,
        }
        items.append(item)

    duration_ms = round((time.time() - start) * 1000, 2)

    # ── Record search in history ──────────────────────────────────
    await _record_search_history(db, search, total, duration_ms, user_id)

    pages = max(1, (total + search.page_size - 1) // search.page_size)

    return {
        "items": items,
        "total": total,
        "page": search.page,
        "page_size": search.page_size,
        "pages": pages,
        "query": search.query,
        "search_duration_ms": duration_ms,
    }


async def _record_search_history(
    db: AsyncSession,
    search: SearchRequest,
    results_count: int,
    duration_ms: float,
    user_id: Optional[int],
):
    """Save a search query to history for analytics."""
    try:
        query_text = search.query or ""
        filters = {}
        for field in ["name", "father_name", "mother_name", "voter_id", "district",
                       "upazila", "union_name", "ward", "occupation"]:
            v = getattr(search, field, None)
            if v:
                filters[field] = v

        history = SearchHistory(
            query=query_text or str(filters),
            filters=filters if filters else None,
            results_count=results_count,
            search_duration_ms=duration_ms,
            user_id=user_id,
        )
        db.add(history)
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record search history: {e}")


# ─── Search Suggestions ───────────────────────────────────────────────────────

async def get_search_suggestions(
    db: AsyncSession,
    query: str,
    field: str = "name",
    limit: int = 10,
) -> List[str]:
    """
    Get autocomplete suggestions for a given field based on existing records.
    Useful for Bengali name autocomplete in the frontend.
    """
    column_map = {
        "name": VoterRecord.name,
        "district": VoterRecord.district,
        "upazila": VoterRecord.upazila,
        "union_name": VoterRecord.union_name,
        "occupation": VoterRecord.occupation,
    }

    column = column_map.get(field)
    if not column:
        return []

    pattern = build_like_pattern(normalize_search_query(query))
    stmt = (
        select(column)
        .where(column.ilike(pattern))
        .where(column.isnot(None))
        .distinct()
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [row[0] for row in result.all() if row[0]]


# ─── District/Upazila Lists ───────────────────────────────────────────────────

async def get_distinct_values(
    db: AsyncSession,
    field: str,
) -> List[str]:
    """Get all distinct values for a field (for filter dropdowns)."""
    column_map = {
        "district": VoterRecord.district,
        "upazila": VoterRecord.upazila,
        "union_name": VoterRecord.union_name,
        "division": VoterRecord.division,
        "gender": VoterRecord.gender,
        "occupation": VoterRecord.occupation,
    }

    column = column_map.get(field)
    if not column:
        return []

    stmt = (
        select(column)
        .where(column.isnot(None))
        .distinct()
        .order_by(column)
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all() if row[0]]
