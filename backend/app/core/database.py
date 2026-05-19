"""
app/core/database.py — Async SQLAlchemy setup.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

_engine = None
_session_maker = None


def _get_database_url() -> str:
    """Get DB URL dynamically at runtime, not at import time."""
    docker_url = os.environ.get("DATABASE_URL", "")
    if docker_url:
        return docker_url
    from app.core.config import get_database_url

    return get_database_url()


def get_engine():
    global _engine
    if _engine is None:
        url = _get_database_url()
        if not url:
            raise ValueError(
                "DATABASE_URL not set. Set DATABASE_URL env var or in .env file. "
                "For docker: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db"
            )
        _engine = create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_async_sessionmaker():
    """Get sessionmaker lazily so env vars are properly loaded."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
