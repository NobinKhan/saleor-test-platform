"""
Seed reference fixture data on official Saleor for L3 golden capture.

Usage:
  python -m app.scripts.seed_reference --url http://saleor-api:8000/graphql/ --email ... --password ...
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import settings
from app.services.reference_seed import seed_reference_data
from app.services.run_helpers import authenticate_saleor


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed reference data for L3 fixtures")
    parser.add_argument("--url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dashboard-version", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    token, err = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(err or "Authentication failed", file=sys.stderr)
        return 1

    ver = args.dashboard_version or settings.reference_baseline_version
    fixtures = await seed_reference_data(
        args.url,
        token,
        timeout=args.timeout,
        dashboard_version=ver,
    )
    keys = sorted(k for k, v in fixtures.items() if v and k != "placeholder_id")
    print(f"Reference seed OK for dashboard-{ver}: {len(keys)} fixture keys")
    for key in keys:
        val = fixtures[key]
        display = str(val)[:48] + ("…" if len(str(val)) > 48 else "")
        print(f"  {key}: {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
