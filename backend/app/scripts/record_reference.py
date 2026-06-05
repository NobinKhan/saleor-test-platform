"""
CLI: record golden reference probes from a Saleor instance.

Usage:
  python -m app.scripts.record_reference --url http://host:8000/graphql/ \\
    --email admin@example.com --password secret
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.database import get_async_sessionmaker
from app.services.reference_capture import capture_reference_probes
from app.services.run_helpers import authenticate_saleor


async def main() -> int:
    parser = argparse.ArgumentParser(description="Record Saleor golden reference corpus")
    parser.add_argument("--url", required=True, help="Saleor GraphQL URL")
    parser.add_argument("--email", required=True, help="Saleor admin email")
    parser.add_argument("--password", required=True, help="Saleor admin password")
    parser.add_argument("--version", default=None, help="Override detected Saleor version")
    parser.add_argument(
        "--scope",
        default="full",
        help="Test scope (full=all introspected endpoints, catalog=static list only)",
    )
    args = parser.parse_args()

    token, auth_error = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(auth_error or "Authentication failed", file=sys.stderr)
        return 1

    async with get_async_sessionmaker()() as db:
        result = await capture_reference_probes(
            saleor_url=args.url,
            saleor_token=token,
            saleor_version=args.version,
            test_scope=args.scope,
            db=db,
            saleor_email=args.email,
            saleor_password=args.password,
        )

    print(f"Captured {result['probe_count']} probes for Saleor {result['saleor_version']}")
    print(f"Corpus: {result['corpus_path']}")
    print(f"Hash: {result['corpus_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
