"""
app/main.py — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import get_async_sessionmaker, get_engine
from app.core.db_migrate import apply_schema_patches
from app.core.security import validate_jwt_secret_for_startup
from app.models import Base
from app.services.reference_capture import sync_corpus_from_disk


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_jwt_secret_for_startup()
    try:
        engine = get_engine()
        url_str = str(engine.url).replace("%", "***")
        print(f"[startup] database URL: {url_str}")
    except Exception as e:
        print(f"[startup] get_engine error: {e}")
    try:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await apply_schema_patches(conn)
        print("[startup] database ready, tables created")
        try:
            async with get_async_sessionmaker()() as db:
                synced = await sync_corpus_from_disk(db)
                if synced:
                    print(f"[startup] synced {synced} golden reference probes from disk")
        except Exception as sync_err:
            print(f"[startup] reference corpus sync skipped: {sync_err}")
    except Exception as e:
        print(f"[startup] db init error: {e}")
        raise
    yield
    await get_engine().dispose()


settings = get_settings()

app = FastAPI(
    title="Saleor Test Platform",
    description="Automated testing platform for Saleor Commerce API",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = (
    [settings.frontend_url]
    if settings.is_production
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.auth import router as auth_router
from app.routes.tests import router as tests_router
from app.routes.reports import router as reports_router
from app.routes.reference import router as reference_router

app.include_router(auth_router)
app.include_router(tests_router)
app.include_router(reports_router)
app.include_router(reference_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
