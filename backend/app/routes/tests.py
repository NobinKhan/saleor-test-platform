"""
app/routes/tests.py — Test run management and live progress via SSE.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, TestRun
from app.schemas import TestRunCreate, TestRunSummary, TestRunDetail, ReportData
from app.services.saleor_auth import fetch_saleor_token
from app.services.sse_manager import runner_manager

router = APIRouter(prefix="/api/runs", tags=["test-runs"])


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TestRunSummary])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    result = await db.execute(
        select(TestRun)
        .where(TestRun.user_id == user.id)
        .order_by(TestRun.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    runs = result.scalars().all()
    out = []
    for r in runs:
        pass_rate = (r.passed / r.total_tests * 100) if r.total_tests > 0 else 0.0
        out.append(TestRunSummary(
            id=r.id,
            saleor_url=r.saleor_url,
            saleor_version=r.saleor_version,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            total_tests=r.total_tests,
            passed=r.passed,
            failed=r.failed,
            warnings=r.warnings,
            skipped=r.skipped,
            pass_rate=round(pass_rate, 1),
        ))
    return out


# ─── Create — starts the test runner ─────────────────────────────────────────

@router.post("", response_model=TestRunSummary)
async def create_run(
    data: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    saleor_token = data.saleor_token

    # Auto-fetch token from Saleor if email+password provided
    if not saleor_token and data.saleor_email and data.saleor_password:
        token, error = await fetch_saleor_token(
            data.saleor_url,
            data.saleor_email,
            data.saleor_password,
        )
        if error:
            raise HTTPException(400, f"Saleor authentication failed: {error}")
        saleor_token = token

    run = TestRun(
        user_id=user.id,
        saleor_url=data.saleor_url,
        saleor_token=saleor_token or "",
        test_scope=data.test_scope,
        public_only=data.public_only,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Kick off the runner (DB persistence happens in background via runner_manager)
    runner_manager.start_run(
        run_id=run.id,
        saleor_url=data.saleor_url,
        saleor_token=saleor_token,
        test_scope=data.test_scope,
        public_only=data.public_only,
    )

    return TestRunSummary(
        id=run.id,
        saleor_url=run.saleor_url,
        saleor_version=run.saleor_version,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_tests=run.total_tests,
        passed=run.passed,
        failed=run.failed,
        warnings=run.warnings,
        skipped=run.skipped,
        pass_rate=0.0,
    )


# ─── Get one ──────────────────────────────────────────────────────────────────

@router.get("/{run_id}", response_model=TestRunDetail)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")
    pass_rate = (run.passed / run.total_tests * 100) if run.total_tests > 0 else 0.0
    return TestRunDetail(
        id=run.id,
        saleor_url=run.saleor_url,
        saleor_version=run.saleor_version,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_tests=run.total_tests,
        passed=run.passed,
        failed=run.failed,
        warnings=run.warnings,
        skipped=run.skipped,
        pass_rate=round(pass_rate, 1),
        user_id=run.user_id,
        saleor_token="***",
        test_scope=run.test_scope,
        public_only=run.public_only,
    )


# ─── Stop ─────────────────────────────────────────────────────────────────────

@router.delete("/{run_id}", status_code=204)
async def stop_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    runner_manager.stop_run(str(run_id))
    run.status = "stopped"
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()


# ─── SSE stream — reads live from the runner manager ───────────────────────────

@router.get("/{run_id}/stream")
async def stream_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify access
    result = await db.execute(
        select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Test run not found")

    # Get or create runner — if this is a fresh GET (e.g. user refreshed during a run)
    runner = runner_manager.get_runner(str(run_id))

    async def event_generator() -> AsyncGenerator[str, None]:
        # If runner is already running, stream from it
        if runner:
            async for event in runner.run():
                event["run_id"] = str(run_id)
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)

        # Otherwise the run is already done — send a completion event
        else:
            run = await db.get(TestRun, run_id)
            if run:
                data = {
                    "type": "complete",
                    "run_id": str(run_id),
                    "total": run.total_tests,
                    "passed": run.passed,
                    "failed": run.failed,
                    "warnings": run.warnings,
                    "skipped": run.skipped,
                    "status_counts": {
                        "pass": run.passed,
                        "fail": run.failed,
                        "warn": run.warnings,
                        "skip": run.skipped,
                    },
                }
                yield f"data: {json.dumps(data)}\n\n"

    return EventSourceResponse(event_generator())