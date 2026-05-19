"""
app/routes/tests.py — Test run management and live progress via SSE.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.core.crypto import encrypt_token
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_sse
from app.models import User, TestRun, TestResult
from app.schemas import TestRunCreate, TestRunSummary, TestRunDetail, TestResultResponse
from app.services.saleor_auth import fetch_saleor_token
from app.services.sse_manager import runner_manager

router = APIRouter(prefix="/api/runs", tags=["test-runs"])


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
        out.append(
            TestRunSummary(
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
            )
        )
    return out


@router.post("", response_model=TestRunSummary)
async def create_run(
    data: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    saleor_token = data.saleor_token

    if not saleor_token and data.saleor_email and data.saleor_password:
        token, error = await fetch_saleor_token(
            data.saleor_url,
            data.saleor_email,
            data.saleor_password,
        )
        if error:
            raise HTTPException(400, f"Saleor authentication failed: {error}")
        saleor_token = token

    ref_url = data.reference_saleor_url or settings.reference_saleor_url or None
    ref_token = data.reference_saleor_token

    run = TestRun(
        user_id=user.id,
        saleor_url=data.saleor_url,
        saleor_token=encrypt_token(saleor_token or ""),
        test_scope=data.test_scope,
        public_only=data.public_only,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    runner_manager.start_run(
        run_id=run.id,
        saleor_url=data.saleor_url,
        saleor_token=saleor_token,
        test_scope=data.test_scope,
        public_only=data.public_only,
        concurrency=data.concurrency,
        timeout_seconds=data.timeout_seconds,
        categories=data.categories,
        reference_saleor_url=ref_url,
        reference_saleor_token=ref_token,
    )

    return TestRunSummary(
        id=run.id,
        saleor_url=run.saleor_url,
        saleor_version=run.saleor_version,
        status="running",
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_tests=run.total_tests,
        passed=run.passed,
        failed=run.failed,
        warnings=run.warnings,
        skipped=run.skipped,
        pass_rate=0.0,
    )


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


@router.get("/{run_id}/results", response_model=list[TestResultResponse])
async def list_results(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    run_result = await db.execute(
        select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id)
    )
    if not run_result.scalar_one_or_none():
        raise HTTPException(404, "Test run not found")

    result = await db.execute(
        select(TestResult)
        .where(TestResult.test_run_id == run_id)
        .order_by(TestResult.created_at)
        .offset(offset)
        .limit(limit)
    )
    return [TestResultResponse.model_validate(r) for r in result.scalars().all()]


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


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_sse),
):
    result = await db.execute(
        select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    rid = str(run_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'connected', 'run_id': rid, 'status': run.status})}\n\n"

        if runner_manager.is_active(rid):
            async for event in runner_manager.subscribe(rid):
                event["run_id"] = rid
                yield f"data: {json.dumps(event)}\n\n"
        elif run.status in ("completed", "stopped", "failed"):
            async for event in runner_manager.replay_from_db(run_id):
                event["run_id"] = rid
                yield f"data: {json.dumps(event)}\n\n"
        else:
            # Run marked active in DB but worker not attached — replay whatever was persisted
            async for event in runner_manager.replay_from_db(run_id):
                event["run_id"] = rid
                yield f"data: {json.dumps(event)}\n\n"
            if run.status in ("running", "pending"):
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Waiting for test worker...', 'run_id': rid})}\n\n"

    return EventSourceResponse(
        event_generator(),
        ping=15,
        media_type="text/event-stream",
    )
