"""
Verify reference corpus integrity (probe count, hash) and L3 client bundles.

Usage:
  python -m app.scripts.verify_corpus --min-probes 100
  python -m app.scripts.verify_corpus --url http://host/graphql/ --email ... --password ...
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_async_sessionmaker
from app.models import TestResult, TestRun
from app.services.client_bundle_schema_gate import compute_client_bundle_schema_gate
from app.services.client_bundles import (
    bundles_compatible_with_schema,
    bundles_hash,
    is_stub_bundle,
    load_all_bundles_from_disk,
    load_bundle_manifest,
)
from app.services.dashboard_bundle_import import root_fields_in_document
from app.services.introspection import introspect_saleor
from app.services.reference_corpus import corpus_hash, load_all_probes_from_disk, load_manifest
from app.services.run_helpers import authenticate_saleor


async def check_corpus(min_probes: int, version: str) -> tuple[bool, str]:
    probes = load_all_probes_from_disk(version)
    manifest = load_manifest(version)
    count = len(probes)
    if count < min_probes:
        return False, f"Reference corpus has {count} probes (need >= {min_probes})"
    chash = corpus_hash(version)
    if manifest and manifest.get("corpus_hash") and manifest["corpus_hash"] != chash:
        return False, "Corpus hash mismatch — re-run record-reference"
    return True, f"Reference corpus OK: {count} probes, hash {chash[:20]}…"


async def check_client_bundles(
    *,
    dashboard_version: str,
    min_bundles: int,
    min_recorded_ratio: float,
    saleor_url: str | None = None,
    saleor_token: str | None = None,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    bundles = load_all_bundles_from_disk("dashboard", dashboard_version)
    manifest = load_bundle_manifest("dashboard", dashboard_version) or {}

    if len(bundles) < min_bundles:
        return False, [f"L3 bundles: {len(bundles)} on disk (need >= {min_bundles})"]

    stubs = [b.bundle_id for b in bundles if is_stub_bundle(b)]
    if stubs:
        return False, [f"L3 stub bundles detected: {', '.join(stubs[:5])}"]

    recorded = sum(1 for b in bundles if b.has_golden())
    ratio = recorded / len(bundles) if bundles else 0.0
    if ratio < min_recorded_ratio:
        return False, [
            f"L3 recorded ratio {ratio:.1%} < {min_recorded_ratio:.0%} "
            f"({recorded}/{len(bundles)})"
        ]

    expected_hash = manifest.get("bundles_hash") or ""
    actual_hash = bundles_hash("dashboard", dashboard_version)
    if expected_hash and expected_hash != actual_hash:
        return False, ["L3 bundles_hash mismatch — re-run patch-corpus --sync-client"]

    for bundle in bundles:
        try:
            root_fields_in_document(bundle.document)
        except Exception as exc:
            return False, [f"L3 bundle {bundle.bundle_id} document parse error: {exc}"]

    messages.append(
        f"L3 bundles OK: {len(bundles)} imported, {recorded} recorded ({ratio:.1%})"
    )

    if saleor_url and saleor_token:
        intro = await introspect_saleor(saleor_url, saleor_token)
        recorded = [b for b in bundles if b.has_golden()]
        compatible, excluded = bundles_compatible_with_schema(recorded, intro)
        if not compatible:
            return False, ["L3 schema gate FAIL: no recorded bundles match target schema"]
        gate = compute_client_bundle_schema_gate(compatible, intro, recorded_only=False)
        if not gate["client_schema_gate_pass"]:
            missing = gate.get("missing_l3_fields") or []
            return False, [f"L3 schema gate FAIL: {len(missing)} missing root field(s)"]
        if excluded:
            messages.append(
                f"L3 schema gate: {len({e['bundle_id'] for e in excluded})} dashboard-only "
                f"bundle(s) excluded (fields not on target Saleor)"
            )
        messages.append(
            f"L3 schema gate PASS ({len(compatible)} certification bundle(s) checked)"
        )

    return True, messages


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
            return False, "No reference comparisons in this run"
        rate = matched / compared * 100
        if rate < min_match:
            return False, f"Match rate {rate:.1f}% < {min_match}% ({matched}/{compared})"
        return True, f"Match rate {rate:.1f}% ({matched}/{compared})"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Verify reference corpus integrity")
    parser.add_argument("--min-probes", type=int, default=100, help="Minimum probe files in corpus")
    parser.add_argument("--min-client-bundles", type=int, default=50, help="Minimum L3 bundle count")
    parser.add_argument(
        "--min-client-recorded-ratio",
        type=float,
        default=0.5,
        help="Minimum fraction of L3 bundles with golden recorded",
    )
    parser.add_argument("--min-match", type=float, default=None, help="Minimum match %% for --run-id")
    parser.add_argument("--run-id", default=None, help="Test run UUID to check")
    parser.add_argument("--version", default=None, help="Corpus Saleor version")
    parser.add_argument("--dashboard-version", default=None, help="L3 dashboard bundle version")
    parser.add_argument("--url", default=None, help="Saleor URL for L3 schema gate check")
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()
    version = args.version or settings.golden_corpus_version
    dashboard_version = args.dashboard_version or settings.reference_baseline_version

    ok, msg = await check_corpus(args.min_probes, version)
    print(msg)
    if not ok:
        return 1

    token = None
    if args.url and args.email and args.password:
        token, err = await authenticate_saleor(args.url, args.email, args.password)
        if not token:
            print(err or "Authentication failed")
            return 1

    l3_ok, l3_msgs = await check_client_bundles(
        dashboard_version=dashboard_version,
        min_bundles=args.min_client_bundles,
        min_recorded_ratio=args.min_client_recorded_ratio,
        saleor_url=args.url,
        saleor_token=token,
    )
    for line in l3_msgs:
        print(line)
    if not l3_ok:
        return 1

    if args.min_match is not None and args.run_id:
        run_ok, run_msg = await check_run_match_rate(uuid.UUID(args.run_id), args.min_match)
        print(run_msg)
        return 0 if run_ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
