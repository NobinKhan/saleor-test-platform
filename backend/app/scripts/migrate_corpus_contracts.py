"""
Add golden_contract, http_status, probe_stability to existing corpus probe files.

Usage:
  python -m app.scripts.migrate_corpus_contracts --version 3.23.7
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.reference_corpus import CORPUS_ROOT, corpus_dir_for_version, probe_filename
from app.services.response_contract import classify_response_contract, infer_probe_stability


def migrate_version(version: str) -> int:
    probes_dir = corpus_dir_for_version(version) / "probes"
    if not probes_dir.is_dir():
        print(f"No probes dir for {version}")
        return 1

    updated = 0
    for path in sorted(probes_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("golden_contract"):
            continue
        resp = data.get("golden_response") or {}
        http_status = data.get("http_status") or 200
        if resp.get("errors") and http_status == 200:
            http_status = 400
        contract = classify_response_contract(resp, http_status=http_status)
        kind = data.get("endpoint_kind", "QUERY")
        data["golden_contract"] = contract
        data["http_status"] = http_status
        data["probe_stability"] = infer_probe_stability(contract, kind)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        updated += 1

    print(f"Migrated {updated} probes in saleor-{version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="3.23.7")
    args = parser.parse_args()
    return migrate_version(args.version)


if __name__ == "__main__":
    raise SystemExit(main())
