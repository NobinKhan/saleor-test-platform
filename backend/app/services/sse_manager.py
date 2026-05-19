"""
app/services/sse_manager.py — Manages active SSE streams and persists test results to DB.
Uses per-run event queues so subscribers never re-invoke TestRunner.run().
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.crypto import decrypt_token
from app.core.database import get_async_sessionmaker
from app.models import TestRun, TestResult
from app.services.test_runner import TestRunner


class _RunState:
    def __init__(self):
        self.subscribers: list[asyncio.Queue[dict | None]] = []
        self.done = False
        self.buffer: list[dict] = []

    def append_buffer(self, event: dict, max_size: int = 500) -> None:
        if event.get("type") == "_stream_end":
            return
        self.buffer.append(event)
        if len(self.buffer) > max_size:
            self.buffer = self.buffer[-max_size:]


class SSERunnerManager:
    """Manages active test runners, event bus, and DB persistence."""

    def __init__(self):
        self._runners: dict[str, TestRunner] = {}
        self._states: dict[str, _RunState] = {}

    def _state(self, run_id: str) -> _RunState:
        if run_id not in self._states:
            self._states[run_id] = _RunState()
        return self._states[run_id]

    def _broadcast(self, run_id: str, event: dict) -> None:
        state = self._state(run_id)
        state.append_buffer(event)
        for q in list(state.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def start_run(
        self,
        run_id: uuid.UUID,
        saleor_url: str,
        saleor_token: str | None,
        test_scope: str,
        public_only: bool,
        concurrency: int = 5,
        timeout_seconds: int = 30,
        categories: list[str] | None = None,
        reference_saleor_url: str | None = None,
        reference_saleor_token: str | None = None,
    ):
        token = decrypt_token(saleor_token) if saleor_token else None
        ref_token = decrypt_token(reference_saleor_token) if reference_saleor_token else None

        runner = TestRunner(
            run_id=run_id,
            saleor_url=saleor_url,
            saleor_token=token,
            test_scope=test_scope,
            public_only=public_only,
            concurrency=concurrency,
            timeout=timeout_seconds,
            categories=categories,
            reference_saleor_url=reference_saleor_url,
            reference_saleor_token=ref_token,
        )
        rid = str(run_id)
        self._runners[rid] = runner
        self._state(rid).done = False
        asyncio.create_task(self._run_and_persist(runner))
        return runner

    async def _run_and_persist(self, runner: TestRunner):
        rid = str(runner.run_id)
        try:
            async with get_async_sessionmaker()() as db:
                run = await db.get(TestRun, runner.run_id)
                if run:
                    run.status = "running"
                    run.started_at = datetime.now(timezone.utc)
                    await db.commit()

            async for event in runner.run():
                self._broadcast(rid, event)
                await self._persist_event(runner.run_id, event)

            self._state(rid).done = True
            self._broadcast(rid, {"type": "_stream_end"})
            key = rid
            if key in self._runners:
                del self._runners[key]

        except Exception:
            async with get_async_sessionmaker()() as s:
                r = await s.get(TestRun, runner.run_id)
                if r:
                    r.status = "failed"
                    r.completed_at = datetime.now(timezone.utc)
                    await s.commit()
            self._state(rid).done = True
            self._broadcast(rid, {"type": "_stream_end"})
            if rid in self._runners:
                del self._runners[rid]

    async def _persist_event(self, run_id: uuid.UUID, event: dict) -> None:
        event_type = event.get("type")

        if event_type == "version":
            async with get_async_sessionmaker()() as s:
                r = await s.get(TestRun, run_id)
                if r:
                    r.saleor_version = event.get("version")
                    await s.commit()

        elif event_type == "schema_diff":
            async with get_async_sessionmaker()() as s:
                r = await s.get(TestRun, run_id)
                if r:
                    existing = r.schema_diff or {}
                    if isinstance(existing, dict):
                        existing.update(event.get("diff", {}))
                        r.schema_diff = existing
                    else:
                        r.schema_diff = event.get("diff", {})
                    await s.commit()

        elif event_type == "result":
            async with get_async_sessionmaker()() as s:
                r = await s.get(TestRun, run_id)
                counts = event.get("status_counts", {})
                if r:
                    r.passed = counts.get("pass", r.passed)
                    r.failed = counts.get("fail", r.failed)
                    r.warnings = counts.get("warn", r.warnings)
                    r.skipped = counts.get("skip", r.skipped)

                result = TestResult(
                    test_run_id=run_id,
                    endpoint_name=event.get("current_endpoint", ""),
                    endpoint_kind=event.get("endpoint_kind", ""),
                    category=event.get("category", ""),
                    is_public=event.get("is_public", False),
                    status=event.get("status", "skip"),
                    error_message=event.get("error_message"),
                    input_sent=event.get("input_sent"),
                    actual_response=event.get("actual_response"),
                    response_time_ms=event.get("response_time_ms"),
                )
                s.add(result)
                await s.commit()

        elif event_type == "complete":
            async with get_async_sessionmaker()() as s:
                r = await s.get(TestRun, run_id)
                if r:
                    r.status = "completed"
                    r.completed_at = datetime.now(timezone.utc)
                    r.total_tests = event.get("total", 0)
                    r.passed = event.get("passed", 0)
                    r.failed = event.get("failed", 0)
                    r.warnings = event.get("warnings", 0)
                    r.skipped = event.get("skipped", 0)
                    await s.commit()

    def stop_run(self, run_id: str):
        if run_id in self._runners:
            self._runners[run_id].stop()

    def get_runner(self, run_id: str) -> TestRunner | None:
        return self._runners.get(run_id)

    def is_active(self, run_id: str) -> bool:
        return run_id in self._runners

    async def subscribe(self, run_id: str) -> AsyncGenerator[dict, None]:
        """Yield buffered events first, then live events until complete."""
        state = self._state(run_id)
        for event in list(state.buffer):
            yield event

        if state.done:
            return

        queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=256)
        state.subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                if event is None or event.get("type") == "_stream_end":
                    break
                yield event
        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)

    async def replay_from_db(self, run_id: uuid.UUID) -> AsyncGenerator[dict, None]:
        """Replay stored results for a finished run."""
        async with get_async_sessionmaker()() as db:
            run = await db.get(TestRun, run_id)
            if not run:
                return

            if run.saleor_version:
                yield {"type": "version", "version": run.saleor_version, "run_id": str(run_id)}

            if run.schema_diff:
                yield {
                    "type": "schema_diff",
                    "diff": run.schema_diff,
                    "run_id": str(run_id),
                }

            result = await db.execute(
                select(TestResult)
                .where(TestResult.test_run_id == run_id)
                .order_by(TestResult.created_at)
            )
            rows = result.scalars().all()
            total = run.total_tests or len(rows)
            counts = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}
            for i, row in enumerate(rows, start=1):
                st = row.status
                if st in counts:
                    counts[st] += 1
                yield {
                    "type": "result",
                    "run_id": str(run_id),
                    "current": i,
                    "total": total,
                    "current_endpoint": row.endpoint_name,
                    "status": row.status,
                    "endpoint_kind": row.endpoint_kind,
                    "category": row.category,
                    "is_public": row.is_public,
                    "response_time_ms": row.response_time_ms,
                    "error_message": row.error_message,
                    "status_counts": dict(counts),
                }

            yield {
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


runner_manager = SSERunnerManager()
