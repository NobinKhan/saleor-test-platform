"""
Patch reference corpus incrementally — record subset, remove ops, apply last diff, sync L3 bundles.

Usage:
  python -m app.scripts.patch_corpus --url ... --email ... --password ... --ops checkout,productCreate
  python -m app.scripts.patch_corpus --url ... --remove checkout__QUERY
  python -m app.scripts.patch_corpus --url ... --apply-diff
  python -m app.scripts.patch_corpus --url ... --sync-client
  python -m app.scripts.patch_corpus --url ... --client-bundles all
  python -m app.scripts.patch_corpus --url ... --client-bundles storefront:all
  python -m app.scripts.patch_corpus --url ... --scenarios product-lifecycle
  python -m app.scripts.patch_corpus --url ... --variants productCreate
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import settings
from app.core.database import get_async_sessionmaker
from app.scripts.corpus_diff import compute_corpus_diff, load_diff_report, save_diff_report
from app.services.client_bundles import remove_client_bundles
from app.services.client_bundle_record import (
    record_client_bundles,
    record_dashboard_bundles,
    record_storefront_bundles,
    save_record_failures,
)
from app.services.dashboard_bundle_import import sync_client_bundles_from_vendor
from app.services.storefront_bundle_import import sync_storefront_bundles_from_vendor
from app.services.catalog_sync import sync_catalog_from_diff
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


def _parse_client_bundle_targets(raw: str) -> list[tuple[str, list[str] | None]]:
    """Parse --client-bundles: all | dashboard:all | storefront:bundle-id."""
    raw = raw.strip()
    if raw.lower() == "all":
        return [("dashboard", None), ("storefront", None)]
    targets: list[tuple[str, list[str] | None]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            source, bundle_part = part.split(":", 1)
            source = source.strip().lower()
            bundle_part = bundle_part.strip()
            bundle_ids = None if bundle_part.lower() == "all" else [bundle_part]
            targets.append((source, bundle_ids))
        else:
            targets.append(("dashboard", [part]))
    return targets


async def _apply_client_diff(
    *,
    saleor_url: str,
    token: str,
    dashboard_version: str,
    storefront_version: str,
    diff,
    email: str,
    password: str,
) -> None:
    for source, bundle_diff in (
        ("dashboard", diff.client_bundles),
        ("storefront", diff.storefront_bundles),
    ):
        if bundle_diff.removed:
            removed = remove_client_bundles(source, dashboard_version if source == "dashboard" else storefront_version, bundle_diff.removed)
            print(f"Removed {removed} {source} bundle(s)")
        if bundle_diff.added or bundle_diff.changed:
            if source == "dashboard":
                sync_client_bundles_from_vendor(dashboard_version)
            else:
                sync_storefront_bundles_from_vendor(storefront_version)
            to_record = bundle_diff.added + bundle_diff.changed
            if to_record:
                record_fn = record_dashboard_bundles if source == "dashboard" else record_storefront_bundles
                result = await record_fn(
                    saleor_url=saleor_url,
                    saleor_token=token,
                    version=dashboard_version if source == "dashboard" else storefront_version,
                    bundle_ids=to_record,
                )
                save_record_failures(source, dashboard_version if source == "dashboard" else storefront_version, result.get("errors") or [])
                print(f"Recorded {result['recorded']} {source} bundle(s)")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally patch reference corpus")
    parser.add_argument("--url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--version", default=None, help="L1 corpus Saleor version")
    parser.add_argument("--dashboard-version", default=None, help="L3 dashboard bundle version")
    parser.add_argument("--storefront-version", default=None, help="L3 storefront bundle version")
    parser.add_argument("--ops", default=None, help="Comma-separated op names or name__KIND")
    parser.add_argument("--remove", default=None, help="Comma-separated L1 ops or L3 bundle IDs")
    parser.add_argument("--apply-diff", action="store_true", help="Apply last corpus-diff report")
    parser.add_argument("--replace", action="store_true", help="Overwrite named probes only")
    parser.add_argument("--sync-client", action="store_true", help="Import L3 bundles from vendor trees")
    parser.add_argument(
        "--client-bundles",
        default=None,
        help="Record L3 golden: all | dashboard:all | storefront:all | bundle-id",
    )
    parser.add_argument(
        "--strip-debug-golden",
        action="store_true",
        help="Strip Python debug fields from L1 golden on disk",
    )
    parser.add_argument(
        "--scenarios",
        default=None,
        help="Record scenario step goldens (comma-separated scenario IDs)",
    )
    parser.add_argument(
        "--variants",
        default=None,
        help="Record input variant goldens (comma-separated operation names)",
    )
    parser.add_argument(
        "--seed-profile",
        default=None,
        help="Fixture seed profile for scenario recording (e.g. harness, saleor_demo)",
    )
    args = parser.parse_args()

    dashboard_version = args.dashboard_version or settings.reference_baseline_version
    storefront_version = args.storefront_version or settings.reference_baseline_version

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
        dash = sync_client_bundles_from_vendor(dashboard_version)
        sf = sync_storefront_bundles_from_vendor(storefront_version)
        print(
            f"Synced {dash['imported']} dashboard + {sf['imported']} storefront bundle(s) "
            f"(P0: {dash['p0_count']}+{sf['p0_count']})"
        )
        return 0

    token, err = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(err or "Authentication failed", file=sys.stderr)
        return 1

    version = args.version or await detect_saleor_version(args.url, token, 30)
    if not version:
        version = settings.golden_corpus_version

    if args.scenarios:
        from app.services.scenario_variant_record import record_scenario
        from app.services.fixture_resolver import resolve_fixtures

        resolution = await resolve_fixtures(args.url, token, timeout=30, seed_profile=args.seed_profile)
        fixtures = resolution.fixtures
        for scenario_id in [s.strip() for s in args.scenarios.split(",") if s.strip()]:
            result = await record_scenario(
                saleor_url=args.url,
                saleor_token=token,
                scenario_id=scenario_id,
                fixtures=fixtures,
                timeout=30,
            )
            print(
                f"Scenario {scenario_id}: recorded {result.get('recorded', 0)}/"
                f"{result.get('total', 0)} step(s)"
            )
        if not args.client_bundles and not args.apply_diff and not args.ops and not args.remove and not args.variants:
            return 0

    if args.variants:
        from app.services.scenario_variant_record import record_operation_variants
        for op_name in [v.strip() for v in args.variants.split(",") if v.strip()]:
            result = await record_operation_variants(
                saleor_url=args.url,
                saleor_token=token,
                operation_name=op_name,
                timeout=30,
            )
            print(
                f"Variants {op_name}: recorded {result.get('recorded', 0)}/"
                f"{result.get('total', 0)}"
            )
        if not args.client_bundles and not args.apply_diff and not args.ops and not args.remove:
            return 0

    if args.sync_client:
        dash = sync_client_bundles_from_vendor(dashboard_version)
        sf = sync_storefront_bundles_from_vendor(storefront_version)
        print(
            f"Synced {dash['imported']} dashboard + {sf['imported']} storefront bundle(s)"
        )
        if not args.client_bundles and not args.apply_diff and not args.ops and not args.remove:
            return 0

    if args.client_bundles:
        for source, bundle_ids in _parse_client_bundle_targets(args.client_bundles):
            ver = dashboard_version if source == "dashboard" else storefront_version
            record_fn = record_dashboard_bundles if source == "dashboard" else record_storefront_bundles
            result = await record_fn(
                saleor_url=args.url,
                saleor_token=token,
                version=ver,
                bundle_ids=bundle_ids,
            )
            save_record_failures(source, ver, result.get("errors") or [])
            print(f"Recorded {result['recorded']} {source} bundle(s) for {source}-{ver}")
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
            removed_d = remove_client_bundles("dashboard", dashboard_version, ids)
            removed_s = remove_client_bundles("storefront", storefront_version, ids)
            print(f"Removed {removed_d + removed_s} client bundle(s)")
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
            catalog_removed = sync_catalog_from_diff(diff.removed)
            if catalog_removed:
                print(f"Removed {catalog_removed} entry(ies) from test_runner catalog")
        await _apply_client_diff(
            saleor_url=args.url,
            token=token,
            dashboard_version=dashboard_version,
            storefront_version=storefront_version,
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
            storefront_version=storefront_version,
        )
        save_diff_report(version, diff, dashboard_version=dashboard_version, storefront_version=storefront_version)
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
        storefront_version=storefront_version,
    )
    save_diff_report(version, diff, dashboard_version=dashboard_version, storefront_version=storefront_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
