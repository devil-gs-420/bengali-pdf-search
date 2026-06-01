"""
Database Configuration: Async SQLAlchemy engine, session factory, and Base model.
Supports both SQLite (development) and PostgreSQL (production).
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ─── Engine Setup ─────────────────────────────────────────────────────────────

# SQLite requires special connect_args; PostgreSQL does not
connect_args = {}
engine_kwargs = {
    "echo": settings.DEBUG,
}

if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine_kwargs["connect_args"] = connect_args
else:
    # PostgreSQL connection pool settings
    engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_pre_ping": True,  # Detect stale connections
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# ─── Session Factory ──────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-loading errors after commit
    autocommit=False,
    autoflush=False,
)


# ─── Declarative Base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Base class for all ORM models with common utilities."""
    pass


# ─── Dependency ───────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    Automatically commits on success and rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
