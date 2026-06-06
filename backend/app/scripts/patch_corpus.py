"""
Patch reference corpus incrementally — record subset, remove ops, apply last diff, sync L3 bundles.

Usage:
  python -m app.scripts.patch_corpus --url ... --email ... --password ... --ops checkout,productCreate
  python -m app.scripts.patch_corpus --url ... --remove checkout__QUERY
  python -m app.scripts.patch_corpus --url ... --apply-diff
  python -m app.scripts.patch_corpus --url ... --sync-client
  python -m app.scripts.patch_corpus --url ... --client-bundles all
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import settings
from app.core.database import get_async_sessionmaker
from app.scripts.corpus_diff import compute_corpus_diff, load_diff_report, save_diff_report
from app.services.client_bundles import remove_client_bundles
from app.services.client_bundle_record import record_dashboard_bundles, save_record_failures
from app.services.dashboard_bundle_import import sync_client_bundles_from_vendor
from app.services.reference_capture import capture_subset_probes, remove_corpus_ops
from app.services.run_helpers import authenticate_saleor
from app.services.test_runner import detect_saleor_version


def _parse_ops(raw: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "__" in part:
            name, kind = part.rsplit("__", 1)
            result.append((name, kind.upper()))
        else:
            result.append((part, "QUERY"))
            result.append((part, "MUTATION"))
    return result


def _parse_bundle_ids(raw: str) -> list[str] | None:
    if raw.strip().lower() == "all":
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def _save_record_failures(version: str, errors: list[str]) -> None:
    save_record_failures(version, errors)


async def _apply_client_diff(
    *,
    saleor_url: str,
    token: str,
    dashboard_version: str,
    diff,
    email: str,
    password: str,
) -> None:
    if diff.client_bundles.removed:
        removed = remove_client_bundles("dashboard", dashboard_version, diff.client_bundles.removed)
        print(f"Removed {removed} client bundle(s)")
    if diff.client_bundles.added or diff.client_bundles.changed:
        sync_client_bundles_from_vendor(dashboard_version)
    to_record = diff.client_bundles.added + diff.client_bundles.changed
    if to_record:
        result = await record_dashboard_bundles(
            saleor_url=saleor_url,
            saleor_token=token,
            version=dashboard_version,
            bundle_ids=to_record,
        )
        _save_record_failures(dashboard_version, result.get("errors") or [])
        print(f"Recorded {result['recorded']} client bundle(s)")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally patch reference corpus")
    parser.add_argument("--url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--version", default=None, help="L1 corpus Saleor version")
    parser.add_argument("--dashboard-version", default=None, help="L3 dashboard bundle version")
    parser.add_argument("--ops", default=None, help="Comma-separated op names or name__KIND")
    parser.add_argument("--remove", default=None, help="Comma-separated L1 ops or L3 bundle IDs")
    parser.add_argument("--apply-diff", action="store_true", help="Apply last corpus-diff report")
    parser.add_argument("--replace", action="store_true", help="Overwrite named probes only")
    parser.add_argument("--sync-client", action="store_true", help="Import L3 bundles from vendor tree")
    parser.add_argument(
        "--client-bundles",
        default=None,
        help="Record L3 golden for bundle IDs or 'all'",
    )
    parser.add_argument(
        "--strip-debug-golden",
        action="store_true",
        help="Strip Python debug fields from L1 golden_response on disk",
    )
    args = parser.parse_args()

    dashboard_version = args.dashboard_version or settings.reference_baseline_version

    if args.strip_debug_golden:
        from app.services.reference_corpus import strip_debug_golden_corpus

        version = args.version or settings.golden_corpus_version
        count = strip_debug_golden_corpus(version)
        print(f"Stripped debug fields from {count} probe(s) in saleor-{version}")
        if not args.sync_client and not args.client_bundles and not args.apply_diff and not args.ops and not args.remove:
            return 0

    if (
        args.sync_client
        and not args.client_bundles
        and not args.apply_diff
        and not args.ops
        and not args.remove
    ):
        result = sync_client_bundles_from_vendor(dashboard_version)
        print(
            f"Synced {result['imported']} client bundle(s) for dashboard-{dashboard_version} "
            f"(P0: {result['p0_count']})"
        )
        return 0

    token, err = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(err or "Authentication failed", file=sys.stderr)
        return 1

    version = args.version or await detect_saleor_version(args.url, token, 30)
    if not version:
        version = settings.golden_corpus_version
    dashboard_version = args.dashboard_version or settings.reference_baseline_version

    if args.sync_client:
        result = sync_client_bundles_from_vendor(dashboard_version)
        print(
            f"Synced {result['imported']} client bundle(s) for dashboard-{dashboard_version} "
            f"(P0: {result['p0_count']})"
        )
        if not args.client_bundles and not args.apply_diff and not args.ops and not args.remove:
            return 0

    if args.client_bundles:
        bundle_ids = _parse_bundle_ids(args.client_bundles)
        result = await record_dashboard_bundles(
            saleor_url=args.url,
            saleor_token=token,
            version=dashboard_version,
            bundle_ids=bundle_ids,
        )
        _save_record_failures(dashboard_version, result.get("errors") or [])
        print(f"Recorded {result['recorded']} client bundle(s) for dashboard-{dashboard_version}")
        if result.get("errors"):
            print(f"  {len(result['errors'])} bundle(s) skipped — see record_failures.json")
        if not args.apply_diff and not args.ops and not args.remove:
            return 0

    if args.remove:
        if any("__" in p for p in args.remove.split(",")):
            ops = _parse_ops(args.remove)
            removed = await remove_corpus_ops(version, ops)
            print(f"Removed {removed} probe(s) from saleor-{version}")
        else:
            ids = [p.strip() for p in args.remove.split(",") if p.strip()]
            removed = remove_client_bundles("dashboard", dashboard_version, ids)
            print(f"Removed {removed} client bundle(s) from dashboard-{dashboard_version}")
        return 0

    ops_to_record: list[tuple[str, str]] = []
    if args.apply_diff:
        diff = load_diff_report(version)
        if not diff:
            print("No last_corpus_diff.json — run corpus-diff first", file=sys.stderr)
            return 1
        for key in diff.added + diff.changed:
            if "__" in key:
                name, kind = key.rsplit("__", 1)
                ops_to_record.append((name, kind))
        if diff.removed:
            await remove_corpus_ops(
                version,
                [(k.rsplit("__", 1)[0], k.rsplit("__", 1)[1]) for k in diff.removed if "__" in k],
            )
            print(f"Removed {len(diff.removed)} deprecated probe(s)")
        await _apply_client_diff(
            saleor_url=args.url,
            token=token,
            dashboard_version=dashboard_version,
            diff=diff,
            email=args.email,
            password=args.password,
        )
    elif args.ops:
        ops_to_record = _parse_ops(args.ops)
    elif args.sync_client or args.client_bundles:
        diff = await compute_corpus_diff(
            saleor_url=args.url,
            saleor_token=token,
            version=version,
            dashboard_version=dashboard_version,
        )
        save_diff_report(version, diff)
        return 0
    else:
        print(
            "Specify --ops, --remove, --apply-diff, --sync-client, or --client-bundles",
            file=sys.stderr,
        )
        return 1

    if ops_to_record:
        async with get_async_sessionmaker()() as db:
            result = await capture_subset_probes(
                saleor_url=args.url,
                saleor_token=token,
                saleor_version=version,
                ops=ops_to_record,
                replace=args.replace or args.apply_diff,
                db=db,
                saleor_email=args.email,
                saleor_password=args.password,
            )
        print(f"Patched {result['recorded']} probe(s) for saleor-{version}")
        print(f"Corpus: {result['corpus_path']}")
    elif args.apply_diff and not ops_to_record:
        print("No L1 probes to record from diff")

    diff = await compute_corpus_diff(
        saleor_url=args.url,
        saleor_token=token,
        version=version,
        dashboard_version=dashboard_version,
    )
    save_diff_report(version, diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
