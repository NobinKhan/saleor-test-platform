"""Verify corpus integrity and Saleor version hard gate."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from app.core.config import settings
from app.services.fixture_resolver import validate_preflight
from app.services.saleor_auth import fetch_saleor_token


async def _run(url: str, email: str, password: str, *, allow_patch_drift: bool) -> int:
    token, err = await fetch_saleor_token(url, email, password)
    if err or not token:
        print(f"Auth failed: {err}", file=sys.stderr)
        return 1
    result = await validate_preflight(
        url,
        token,
        corpus_version=settings.golden_corpus_version,
        allow_patch_drift=allow_patch_drift,
    )
    if not result.get("version_gate_pass"):
        reason = result.get("version_gate_reason") or "Version gate failed"
        print(reason, file=sys.stderr)
        return 1
    shop = result.get("shop_version")
    print(f"Shop version: {shop} (corpus {settings.golden_corpus_version})")
    issues = result.get("issues") or []
    if issues:
        for issue in issues:
            print(f"  note: {issue}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Corpus version hard gate check")
    parser.add_argument("--url", default=os.environ.get("REFERENCE_SALEOR_URL", "http://saleor-api:8000/graphql/"))
    parser.add_argument("--email", default=os.environ.get("SALEOR_ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--password", default=os.environ.get("SALEOR_ADMIN_PASSWORD", "admin123456"))
    parser.add_argument(
        "--allow-patch-drift",
        action="store_true",
        default=os.environ.get("ALLOW_PATCH_DRIFT", "").lower() in ("1", "true", "yes"),
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.url, args.email, args.password, allow_patch_drift=args.allow_patch_drift)))


if __name__ == "__main__":
    main()
