"""Idempotent schema patches for existing harness databases."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


_MIGRATIONS: list[str] = [
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS saleor_email TEXT",
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS saleor_password TEXT",
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS reference_baseline_version VARCHAR(50)",
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS reference_baseline_source VARCHAR(100)",
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS concurrency INTEGER DEFAULT 5",
    "ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER DEFAULT 30",
    "ALTER TABLE test_results ADD COLUMN IF NOT EXISTS outcome VARCHAR(40)",
    "ALTER TABLE test_results ADD COLUMN IF NOT EXISTS response_valid BOOLEAN",
    "ALTER TABLE test_results ADD COLUMN IF NOT EXISTS expected_response TEXT",
    "ALTER TABLE test_results ADD COLUMN IF NOT EXISTS match_status VARCHAR(20)",
    "ALTER TABLE test_results ADD COLUMN IF NOT EXISTS diff_summary TEXT",
]


async def apply_schema_patches(conn: AsyncConnection) -> None:
    for stmt in _MIGRATIONS:
        await conn.execute(text(stmt))
