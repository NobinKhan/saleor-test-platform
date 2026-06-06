"""
Compare live Saleor schema/behavior against on-disk reference corpus index and L3 bundles.

Usage:
  python -m app.scripts.corpus_diff --url http://host:8000/graphql/ --email ... --password ...
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.client_bundles import dashboard_vendor_path
from app.services.dashboard_bundle_import import (
    ClientBundleDiff,
    compute_client_bundle_diff,
)
from app.services.introspection import introspect_saleor
from app.services.reference_corpus import (
    corpus_dir_for_version,
    load_all_probes_from_disk,
    load_manifest,
)
from app.services.run_helpers import authenticate_saleor
from app.services.test_runner import detect_saleor_version


@dataclass
class CorpusDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    client_bundles: ClientBundleDiff = field(default_factory=ClientBundleDiff)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "client_bundles": self.client_bundles.to_dict(),
        }


def _op_key(name: str, kind: str) -> str:
    return f"{name}__{kind}"


async def compute_corpus_diff(
    *,
    saleor_url: str,
    saleor_token: str | None,
    version: str,
    dashboard_version: str | None = None,
    timeout: int = 30,
    replay_changed: bool = False,
) -> CorpusDiff:
    manifest = load_manifest(version) or {}
    index = manifest.get("operations_index") or {}
    on_disk = {
        _op_key(p.endpoint_name, p.endpoint_kind): p
        for p in load_all_probes_from_disk(version)
    }

    intro = await introspect_saleor(saleor_url, saleor_token, timeout)
    live_ops: dict[str, dict[str, str]] = {}
    for name in intro.get("queries", []):
        live_ops[_op_key(name, "QUERY")] = {"name": name, "kind": "QUERY"}
    for name in intro.get("mutations", []):
        live_ops[_op_key(name, "MUTATION")] = {"name": name, "kind": "MUTATION"}

    diff = CorpusDiff()
    for key in sorted(live_ops):
        if key not in on_disk and key not in index:
            diff.added.append(key)
        elif key not in on_disk:
            diff.added.append(key)

    for key in sorted(on_disk):
        if key not in live_ops:
            diff.removed.append(key)

    for key in sorted(set(on_disk) & set(live_ops)):
        probe = on_disk[key]
        idx = index.get(key) or {}
        input_hash = hashlib.sha256(probe.input_sent.encode()).hexdigest()[:16]
        if idx.get("input_hash") and idx["input_hash"] != input_hash:
            diff.changed.append(key)
        elif replay_changed and saleor_token:
            pass
        else:
            diff.unchanged.append(key)

    dash_ver = dashboard_version or settings.reference_baseline_version
    vendor = dashboard_vendor_path(dash_ver)
    if vendor.is_dir():
        diff.client_bundles = compute_client_bundle_diff(version=dash_ver)

    return diff


def save_diff_report(
    version: str,
    diff: CorpusDiff,
    dashboard_version: str | None = None,
) -> Path:
    path = corpus_dir_for_version(version) / "last_corpus_diff.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diff.to_dict(), indent=2), encoding="utf-8")
    from app.services.client_bundles import bundle_dir_for_version

    dash_ver = dashboard_version or settings.reference_baseline_version
    mirror = bundle_dir_for_version("dashboard", dash_ver) / "last_corpus_diff.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(diff.client_bundles.to_dict(), indent=2), encoding="utf-8")
    return path


def load_diff_report(version: str) -> CorpusDiff | None:
    path = corpus_dir_for_version(version) / "last_corpus_diff.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    client = ClientBundleDiff.from_dict(data.pop("client_bundles", None))
    return CorpusDiff(client_bundles=client, **data)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Diff live Saleor against reference corpus")
    parser.add_argument("--url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--version", default=None)
    parser.add_argument("--dashboard-version", default=None)
    args = parser.parse_args()

    token, err = await authenticate_saleor(args.url, args.email, args.password)
    if not token:
        print(err or "Authentication failed", file=sys.stderr)
        return 1

    version = args.version or await detect_saleor_version(args.url, token, 30)
    if not version:
        version = settings.golden_corpus_version

    diff = await compute_corpus_diff(
        saleor_url=args.url,
        saleor_token=token,
        version=version,
        dashboard_version=args.dashboard_version,
    )
    report_path = save_diff_report(version, diff)
    cb = diff.client_bundles
    print(f"Corpus diff for saleor-{version}:")
    print(f"  L1 added:     {len(diff.added)}")
    print(f"  L1 removed:   {len(diff.removed)}")
    print(f"  L1 changed:   {len(diff.changed)}")
    print(f"  L1 unchanged: {len(diff.unchanged)}")
    print(f"  L3 added:     {len(cb.added)}")
    print(f"  L3 removed:   {len(cb.removed)}")
    print(f"  L3 changed:   {len(cb.changed)}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
