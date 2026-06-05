"""
CI gate: verify golden corpus integrity or test-run match rate.

Usage:
  python -m app.scripts.golden_gate --min-probes 100
  python -m app.scripts.golden_gate --min-match 90 --run-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_async_sessionmaker
from app.models import TestResult, TestRun
from app.services.reference_corpus import corpus_hash, load_all_probes_from_disk, load_manifest


async def check_corpus(min_probes: int, version: str) -> tuple[bool, str]:
    probes = load_all_probes_from_disk(version)
    manifest = load_manifest(version)
    count = len(probes)
    if count < min_probes:
        return False, f"Golden corpus has {count} probes (need >= {min_probes})"
    chash = corpus_hash(version)
    if manifest and manifest.get("corpus_hash") and manifest["corpus_hash"] != chash:
        return False, "Corpus hash mismatch — re-run record-reference"
    return True, f"Golden corpus OK: {count} probes, hash {chash[:20]}…"


async def check_run_match_rate(run_id: uuid.UUID, min_match: float) -> tuple[bool, str]:
    async with get_async_sessionmaker()() as db:
        run = await db.get(TestRun, run_id)
        if not run:
            return False, f"Run {run_id} not found"
        rows = await db.execute(
            select(TestResult.match_status).where(TestResult.test_run_id == run_id)
        )
        statuses = [r[0] for r in rows.all() if r[0]]
        matched = sum(1 for s in statuses if s == "match")
        compared = sum(1 for s in statuses if s in ("match", "mismatch", "shape_drift"))
        if compared == 0:
            return False, "No golden comparisons in this run"
        rate = matched / compared * 100
        if rate < min_match:
            return False, f"Golden match rate {rate:.1f}% < {min_match}% ({matched}/{compared})"
        return True, f"Golden match rate {rate:.1f}% ({matched}/{compared})"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Golden reference CI gate")
    parser.add_argument("--min-probes", type=int, default=100, help="Minimum probe files in corpus")
    parser.add_argument("--min-match", type=float, default=None, help="Minimum match %% for --run-id")
    parser.add_argument("--run-id", default=None, help="Test run UUID to check")
    parser.add_argument("--version", default=None, help="Corpus Saleor version")
    args = parser.parse_args()
    version = args.version or settings.reference_baseline_version

    ok, msg = await check_corpus(args.min_probes, version)
    print(msg)
    if not ok:
        return 1

    if args.min_match is not None and args.run_id:
        run_ok, run_msg = await check_run_match_rate(uuid.UUID(args.run_id), args.min_match)
        print(run_msg)
        return 0 if run_ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
