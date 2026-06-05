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
from app.services.test_runner import TestRunner


async def run_self_check(
    *,
    url: str,
    email: str,
    password: str,
    min_compat: float,
    version: str,
) -> int:
    token, err = await fetch_saleor_token(url, email, password)
    if err or not token:
        print(f"Auth failed: {err}")
        return 1

    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url=url,
        saleor_token=token,
        test_scope="full",
        test_mode="compatibility",
        use_introspection=True,
        concurrency=1,
        saleor_email=email,
        saleor_password=password,
    )

    from collections import Counter

    total = matched = mismatched = 0
    mismatch_reasons: Counter[str] = Counter()
    async for event in runner.run():
        if event.get("type") == "result":
            total += 1
            ms = event.get("match_status")
            if ms == "match":
                matched += 1
            elif ms in ("mismatch", "shape_drift"):
                mismatched += 1
                mismatch_reasons[event.get("diff_summary", "unknown")[:80]] += 1

    compared = matched + mismatched
    rate = matched / compared * 100 if compared else 0
    print(f"Self-check vs golden {version}: {rate:.1f}% compatible ({matched}/{compared})")
    if mismatched:
        print(f"  Mismatched: {mismatched}")
        for reason, cnt in mismatch_reasons.most_common(8):
            print(f"    {cnt}x {reason}")
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
    parser.add_argument("--min-compat", type=float, default=99.0)
    parser.add_argument("--version", default=None)
    args = parser.parse_args()
    return asyncio.run(
        run_self_check(
            url=args.url,
            email=args.email,
            password=args.password,
            min_compat=args.min_compat,
            version=args.version or settings.golden_corpus_version,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
