"""
app/services/sse_manager.py — Manages active SSE streams and persists test results to DB.
Each stream is keyed by run_id. Creates fresh DB sessions per commit so the
original request's session doesn't get used after the handler returns.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_sessionmaker
from app.models import TestRun, TestResult
from app.services.test_runner import TestRunner


class SSERunnerManager:
    """
    Manages active test runners and persists results to the DB.
    Stores runners by run_id so stop/cancel works.
    """

    def __init__(self):
        self._runners: dict[str, TestRunner] = {}

    def start_run(
        self,
        run_id: uuid.UUID,
        saleor_url: str,
        saleor_token: str | None,
        test_scope: str,
        public_only: bool,
    ):
        """Start a new test runner. DB work happens in a background task with
        fresh sessions, so the caller's session doesn't leak."""
        runner = TestRunner(
            run_id=run_id,
            saleor_url=saleor_url,
            saleor_token=saleor_token,
            test_scope=test_scope,
            public_only=public_only,
        )
        self._runners[str(run_id)] = runner

        # Run in background with fresh sessions for each DB operation
        asyncio.create_task(self._run_and_persist(runner))

        return runner

    async def _run_and_persist(self, runner: TestRunner):
        """Run the test generator and persist each result to the DB.
        Each DB operation gets its own session so we're safe across task boundaries."""
        async with get_async_sessionmaker()() as db:
            try:
                # Mark run as running
                run = await db.get(TestRun, runner.run_id)
                if run:
                    run.status = "running"
                    run.started_at = datetime.now(timezone.utc)
                    await db.commit()

                async for event in runner.run():
                    event_type = event.get("type")

                    if event_type == "version":
                        async with get_async_sessionmaker()() as s:
                            r = await s.get(TestRun, runner.run_id)
                            if r:
                                r.saleor_version = event.get("version")
                                await s.commit()

                    elif event_type == "result":
                        async with get_async_sessionmaker()() as s:
                            r = await s.get(TestRun, runner.run_id)
                            counts = event.get("status_counts", {})
                            if r:
                                r.passed = counts.get("pass", r.passed)
                                r.failed = counts.get("fail", r.failed)
                                r.warnings = counts.get("warn", r.warnings)
                                r.skipped = counts.get("skip", r.skipped)

                            result = TestResult(
                                test_run_id=runner.run_id,
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
                            r = await s.get(TestRun, runner.run_id)
                            if r:
                                r.status = "completed"
                                r.completed_at = datetime.now(timezone.utc)
                                r.total_tests = event.get("total", 0)
                                r.passed = event.get("passed", 0)
                                r.failed = event.get("failed", 0)
                                r.warnings = event.get("warnings", 0)
                                r.skipped = event.get("skipped", 0)
                                await s.commit()

                        # Clean up runner
                        key = str(runner.run_id)
                        if key in self._runners:
                            del self._runners[key]

            except Exception:
                # Mark run as failed
                async with get_async_sessionmaker()() as s:
                    r = await s.get(TestRun, runner.run_id)
                    if r:
                        r.status = "failed"
                        r.completed_at = datetime.now(timezone.utc)
                        await s.commit()
                key = str(runner.run_id)
                if key in self._runners:
                    del self._runners[key]

    def stop_run(self, run_id: str):
        if run_id in self._runners:
            self._runners[run_id].stop()

    def get_runner(self, run_id: str) -> TestRunner | None:
        return self._runners.get(run_id)


# Singleton manager
runner_manager = SSERunnerManager()