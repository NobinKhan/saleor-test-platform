"""
CLI: record golden reference probes from a Saleor instance.

Usage:
  python -m app.scripts.record_reference --url http://host:8000/graphql/ \\
    --email admin@example.com --password secret
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.config import settings
from app.core.database import get_async_sessionmaker
from app.services.client_bundles import bundle_dir_for_version
from app.services.client_bundle_record import record_dashboard_bundles
from app.services.dashboard_bundle_import import sync_client_bundles_from_vendor
from app.services.reference_capture import capture_reference_probes
from app.services.run_helpers import authenticate_saleor


def _save_record_failures(version: str, errors: list[str]) -> None:
    path = bundle_dir_for_version("dashboard", version) / "record_failures.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"errors": errors}, indent=2), encoding="utf-8")


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
    parser.add_argument("--ops", default=None, help="Comma-separated ops for subset capture (delegates to patch)")
    parser.add_argument("--remove", default=None, help="Comma-separated ops to remove from corpus")
    parser.add_argument("--apply-diff", action="store_true", help="Apply last corpus-diff report")
    parser.add_argument("--replace", action="store_true", help="Overwrite named probes only")
    parser.add_argument("--sync-client", action="store_true", help="Import L3 bundles from vendor")
    parser.add_argument("--client-bundles", default=None, help="Record L3 bundles (comma-separated or 'all')")
    parser.add_argument("--no-client-sync", action="store_true", help="Skip automatic L3 sync on full record")
    args = parser.parse_args()

    token, auth_error = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(auth_error or "Authentication failed", file=sys.stderr)
        return 1

    dashboard_version = settings.reference_baseline_version

    if (
        args.ops
        or args.remove
        or args.apply_diff
        or args.sync_client
        or args.client_bundles
    ):
        from app.scripts import patch_corpus

        patch_args = [
            "--url", args.url,
            "--email", args.email,
            "--password", args.password,
        ]
        if args.version:
            patch_args.extend(["--version", args.version])
        if args.ops:
            patch_args.extend(["--ops", args.ops])
        if args.remove:
            patch_args.extend(["--remove", args.remove])
        if args.apply_diff:
            patch_args.append("--apply-diff")
        if args.replace:
            patch_args.append("--replace")
        if args.sync_client:
            patch_args.append("--sync-client")
        if args.client_bundles:
            patch_args.extend(["--client-bundles", args.client_bundles])
        old_argv = sys.argv
        try:
            sys.argv = ["patch_corpus", *patch_args]
            return await patch_corpus.main()
        finally:
            sys.argv = old_argv

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

    if args.scope == "full" and not args.no_client_sync:
        from app.services.reference_seed import seed_reference_data

        print("Seeding reference fixture data for L3 capture…")
        await seed_reference_data(args.url, token, dashboard_version=dashboard_version)
        sync_result = sync_client_bundles_from_vendor(dashboard_version)
        print(
            f"Synced {sync_result['imported']} L3 bundle(s) for dashboard-{dashboard_version}"
        )
        record_result = await record_dashboard_bundles(
            saleor_url=args.url,
            saleor_token=token,
            version=dashboard_version,
            bundle_ids=None,
        )
        _save_record_failures(dashboard_version, record_result.get("errors") or [])
        print(
            f"Recorded {record_result['recorded']} L3 bundle(s) "
            f"({len(record_result.get('errors') or [])} skipped)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
