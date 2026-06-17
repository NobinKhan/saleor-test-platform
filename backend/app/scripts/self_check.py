"""
Self-check: replay golden corpus against official Saleor and verify compatibility.

Usage:
  python -m app.scripts.self_check --url http://saleor-api:8000/graphql/ --email admin@example.com --password admin123456
  python -m app.scripts.self_check --min-compat 99
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from app.core.config import settings
from app.services.saleor_auth import fetch_saleor_token
from app.services.run_scope import FULL_SYSTEM_SCOPE
from app.services.test_runner import TestRunner


async def run_self_check(
    *,
    url: str,
    email: str,
    password: str,
    min_compat: float,
    version: str,
    test_scope: str = FULL_SYSTEM_SCOPE,
    require_tier2: bool = False,
) -> int:
    token, err = await fetch_saleor_token(url, email, password)
    if err or not token:
        print(f"Auth failed: {err}")
        return 1

    if require_tier2:
        runner = TestRunner(
            run_id=uuid.uuid4(),
            saleor_url=url,
            saleor_token=token,
            test_scope=test_scope,
            use_introspection=True,
            concurrency=1,
            saleor_email=email,
            saleor_password=password,
            tier2_required=True,
            demo_seed_profile="harness",
        )
    else:
        runner = TestRunner(
            run_id=uuid.uuid4(),
            saleor_url=url,
            saleor_token=token,
            test_scope=test_scope,
            use_introspection=True,
            concurrency=1,
            saleor_email=email,
            saleor_password=password,
            demo_seed_profile="harness",
        )

    from collections import Counter

    total = matched = mismatched = tier2_fail = 0
    mismatch_reasons: Counter[str] = Counter()
    mismatched_ids: list[str] = []
    async for event in runner.run():
        if event.get("type") == "result":
            total += 1
            ms = event.get("match_status")
            if ms == "match":
                matched += 1
            elif ms == "parity_gap" and not require_tier2:
                matched += 1
            elif ms in ("mismatch", "shape_drift", "tier2_fail"):
                mismatched += 1
                if ms == "tier2_fail":
                    tier2_fail += 1
                mismatch_reasons[event.get("diff_summary", "unknown")[:80]] += 1
                mismatched_ids.append(event.get("probe_id", event.get("bundle_id", "?")))

    compared = matched + mismatched
    if compared < total:
        compared = total
    rate = matched / compared * 100 if compared else 0
    tier_label = "Tier1+Tier2" if require_tier2 else "Tier1"
    print(f"Self-check ({tier_label}, scope={test_scope}) vs {version}: {rate:.1f}% ({matched}/{compared})")
    if tier2_fail:
        print(f"  Tier 2 failures: {tier2_fail}")
    if mismatched:
        print(f"  Mismatched: {mismatched}")
        for reason, cnt in mismatch_reasons.most_common(8):
            print(f"    {cnt}x {reason}")
        for pid in mismatched_ids:
            print(f"    - {pid}")
    if rate < min_compat:
        print(f"FAIL: below threshold {min_compat}%")
        return 1
    print("PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden corpus self-check against Saleor")
    parser.add_argument("--url", default=settings.reference_saleor_url or "http://saleor-api:8000/graphql/")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="admin123456")
    parser.add_argument("--min-compat", type=float, default=100.0)
    parser.add_argument("--version", default=None)
    parser.add_argument("--scope", default=FULL_SYSTEM_SCOPE, help="Test scope (default: full system)")
    parser.add_argument("--require-tier2", action="store_true", help="Enforce SGRC Tier 2 hard gate")
    args = parser.parse_args()
    return asyncio.run(
        run_self_check(
            url=args.url,
            email=args.email,
            password=args.password,
            min_compat=args.min_compat,
            version=args.version or settings.golden_corpus_version,
            test_scope=args.scope,
            require_tier2=args.require_tier2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
