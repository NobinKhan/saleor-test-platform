"""
Derive semantic_profile fields for existing corpus probes.

Usage:
  python -m app.scripts.migrate_semantic_profiles --version 3.23.7
"""

from __future__ import annotations

import argparse
import json

from app.services.reference_corpus import corpus_dir_for_version, update_manifest_after_patch
from app.services.response_contract import classify_response_contract
from app.services.semantic_compare import build_semantic_profile


def _build_profile(data: dict) -> dict | None:
    contract = data.get("golden_contract")
    if not contract:
        resp = data.get("golden_response") or {}
        http_status = data.get("http_status") or 200
        contract = classify_response_contract(resp, http_status=http_status)
    return build_semantic_profile(
        golden_response=data.get("golden_response") or {},
        golden_contract=contract,
        input_sent=data.get("input_sent", ""),
        endpoint_name=data.get("endpoint_name", ""),
    )


def migrate_version(version: str) -> int:
    probes_dir = corpus_dir_for_version(version) / "probes"
    if not probes_dir.is_dir():
        print(f"No probes dir for {version}")
        return 1

    updated = 0
    for path in sorted(probes_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = _build_profile(data)
        if profile == data.get("semantic_profile"):
            continue
        if profile:
            data["semantic_profile"] = profile
        elif "semantic_profile" in data:
            del data["semantic_profile"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        updated += 1

    update_manifest_after_patch(version)
    print(f"Migrated semantic profiles for {updated} probes in saleor-{version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="3.23.7")
    args = parser.parse_args()
    return migrate_version(args.version)


if __name__ == "__main__":
    raise SystemExit(main())
