"""
app/core/database.py — Async SQLAlchemy setup.
"""

from __future__ import annotations

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from functools import lru_cache


def _get_database_url() -> str:
    """Get DB URL dynamically at runtime, not at import time."""
    docker_url = os.environ.get("DATABASE_URL", "")
    if docker_url:
        return docker_url
    # Fallback to pydantic settings if env var not set (e.g., local dev)
    from app.core.config import get_database_url
    return get_database_url()


def _get_db_host() -> str:
    """Return the DB host. Falls back to 172.24.0.3 if 'db' doesn't resolve."""
    try:
        import socket
        socket.gethostbyname("db")
        return "db"
    except socket.gaierror:
        return "172.24.0.3"


def _engine_url() -> str:
    """Always read fresh — do NOT cache. Env vars may not be set at import time."""
    base_url = _get_database_url()
    # Always replace 'db' hostname with direct IP to bypass asyncpg DNS resolution
    # issues inside this container. The IP is stable (DB container has fixed IP).
    if base_url and "@db:" in base_url:
        base_url = base_url.replace("@db:", "@172.24.0.3:")
    return base_url


# Note: The engine is created lazily when first accessed, not at import time
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = _engine_url()
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
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Keep these for backward compatibility with existing code
engine = None  # Lazy-loaded via get_engine()
async_sessionmaker = None  # Lazy-loaded via get_async_sessionmaker()


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