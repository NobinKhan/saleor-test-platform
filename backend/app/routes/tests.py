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

from app.core.crypto import decrypt_token
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_sse
from app.models import User, TestRun, TestResult
from app.schemas import TestRunCreate, TestRunSummary, TestRunDetail, TestResultResponse
from app.services.run_helpers import (
    authenticate_saleor,
    build_test_run_row,
    decrypt_saleor_email,
    run_detail_fields,
)
from app.services.sse_manager import runner_manager

router = APIRouter(prefix="/api/runs", tags=["test-runs"])


def _summary_from_run(run: TestRun) -> TestRunSummary:
    total = run.total_tests or 0
    passed = run.passed or 0
    pass_rate = (passed / total * 100) if total > 0 else 0.0
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
        pass_rate=round(pass_rate, 1),
    )


def _start_runner(
    run: TestRun,
    saleor_token: str,
    categories: list[str] | None = None,
    test_mode: str = "compatibility",
    *,
    saleor_email: str | None = None,
    saleor_password: str | None = None,
    saleor_customer_email: str | None = None,
    saleor_customer_password: str | None = None,
) -> None:
    runner_manager.start_run(
        run_id=run.id,
        saleor_url=run.saleor_url,
        saleor_token=saleor_token,
        test_scope=run.test_scope,
        public_only=run.public_only,
        concurrency=run.concurrency or 5,
        timeout_seconds=run.timeout_seconds or 30,
        categories=categories,
        test_mode=test_mode,
        saleor_email=saleor_email or run.saleor_email,
        saleor_password=saleor_password or run.saleor_password,
        saleor_customer_email=saleor_customer_email,
        saleor_customer_password=saleor_customer_password,
    )


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
    return [_summary_from_run(r) for r in result.scalars().all()]


@router.post("", response_model=TestRunSummary)
async def create_run(
    data: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    saleor_url = data.saleor_url
    saleor_email = str(data.saleor_email)
    saleor_password = data.saleor_password

    if data.clone_from_run_id:
        result = await db.execute(
            select(TestRun).where(
                TestRun.id == data.clone_from_run_id,
                TestRun.user_id == user.id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(404, "Source test run not found")
        if not saleor_password:
            if not source.saleor_password:
                raise HTTPException(
                    400,
                    "Source run has no stored password; enter a password to continue.",
                )
            saleor_password = decrypt_token(source.saleor_password)

    if not saleor_password:
        raise HTTPException(400, "Saleor admin password is required")

    token, error = await authenticate_saleor(saleor_url, saleor_email, saleor_password)
    if error or not token:
        raise HTTPException(400, f"Saleor authentication failed: {error or 'no token'}")

    row = build_test_run_row(
        user_id=user.id,
        saleor_url=saleor_url,
        saleor_email=saleor_email,
        saleor_password=saleor_password,
        saleor_token=token,
        test_scope=data.test_scope,
        public_only=data.public_only,
        concurrency=data.concurrency,
        timeout_seconds=data.timeout_seconds,
    )
    run = TestRun(**row)
    if data.compare_run_id:
        run.schema_diff = {"_compare_run_id": str(data.compare_run_id)}
    db.add(run)
    await db.commit()
    await db.refresh(run)

    _start_runner(
        run,
        token,
        data.categories,
        data.test_mode,
        saleor_email=row["saleor_email"],
        saleor_password=row["saleor_password"],
        saleor_customer_email=data.saleor_customer_email,
        saleor_customer_password=data.saleor_customer_password,
    )
    return _summary_from_run(run)


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

    base = _summary_from_run(run)
    extra = run_detail_fields(run)
    return TestRunDetail(
        **base.model_dump(),
        user_id=run.user_id,
        test_scope=run.test_scope,
        public_only=run.public_only,
        **extra,
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

    def sse_payload(event: dict) -> dict[str, str]:
        return {"data": json.dumps(event)}

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        yield sse_payload({"type": "connected", "run_id": rid, "status": run.status})

        if runner_manager.is_active(rid):
            async for event in runner_manager.subscribe(rid):
                event["run_id"] = rid
                yield sse_payload(event)
        elif run.status in ("completed", "stopped", "failed"):
            async for event in runner_manager.replay_from_db(run_id):
                event["run_id"] = rid
                yield sse_payload(event)
        else:
            async for event in runner_manager.replay_from_db(run_id):
                event["run_id"] = rid
                yield sse_payload(event)
            if run.status in ("running", "pending"):
                yield sse_payload(
                    {
                        "type": "progress",
                        "message": "Waiting for test worker...",
                        "run_id": rid,
                    }
                )

    return EventSourceResponse(
        event_generator(),
        ping=15,
        media_type="text/event-stream",
    )
