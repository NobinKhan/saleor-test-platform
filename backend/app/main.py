"""
app/main.py — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import get_engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    try:
        engine = get_engine()
        url_str = str(engine.url).replace("%", "***")
        print(f"[startup] database URL: {url_str}")
    except Exception as e:
        print(f"[startup] get_engine error: {e}")
    try:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[startup] database ready, tables created")
    except Exception as e:
        print(f"[startup] db init error: {e}")
        raise
    yield
    await get_engine().dispose()


app = FastAPI(
    title="Saleor Test Platform",
    description="Automated testing platform for Saleor Commerce API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.routes.auth import router as auth_router
from app.routes.tests import router as tests_router
from app.routes.reports import router as reports_router

app.include_router(auth_router)
app.include_router(tests_router)
app.include_router(reports_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
