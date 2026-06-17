"""
Lint golden JSON for Saleor populatedb-specific literals.

Mutation-first goldens must not encode demo catalog names, slugs, or emails.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

# Demo-specific literals that must not appear in harness-recorded goldens.
FORBIDDEN_LITERALS: tuple[str, ...] = (
    "Featured Products",
    "Summer Picks",
    "channel-pln",
    "ashley.cook@",
    "jade.guerrero@example.com",
    "apple-juice",
)

# Heuristic: populatedb-era numeric Relay IDs (base64 small integers).
POPULATEDB_ID_RE = re.compile(
    r"UHJvZHVjdDoxNTI=|UHJvZHVjdFZhcmlhbnQ6Mzg0|Q2hhbm5lbDoy"
)


@dataclass(frozen=True)
class LiteralFinding:
    path: str
    message: str
    severity: str  # "warning" | "error"


def iter_golden_json_files() -> list[Path]:
    """Yield golden JSON paths from baked/volume corpus roots (Docker-aware)."""
    from app.services.client_bundles import BUNDLES_ROOT
    from app.services.reference_corpus import CORPUS_ROOT
    from app.services.scenario_corpus import SCENARIOS_ROOT

    files: list[Path] = []
    if CORPUS_ROOT.is_dir():
        files.extend(sorted(CORPUS_ROOT.glob("saleor-*/probes/*.json")))
    if BUNDLES_ROOT.is_dir():
        for path in sorted(BUNDLES_ROOT.glob("*/bundles/*.graphql.json")):
            if not path.name.startswith("_"):
                files.append(path)
        files.extend(sorted(BUNDLES_ROOT.glob("*/fixtures.json")))
    if SCENARIOS_ROOT.is_dir():
        files.extend(sorted(SCENARIOS_ROOT.glob("*/steps/*.json")))
    return files


def _scan_value(value: object, file_path: str, json_path: str, findings: list[LiteralFinding]) -> None:
    if isinstance(value, str):
        for literal in FORBIDDEN_LITERALS:
            if literal in value:
                findings.append(
                    LiteralFinding(
                        path=f"{file_path}:{json_path}",
                        message=f"demo literal {literal!r}",
                        severity="warning",
                    )
                )
        if POPULATEDB_ID_RE.search(value):
            findings.append(
                LiteralFinding(
                    path=f"{file_path}:{json_path}",
                    message="suspected populatedb Relay ID",
                    severity="warning",
                )
            )
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{json_path}.{key}" if json_path else key
            _scan_value(child, file_path, child_path, findings)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _scan_value(child, file_path, f"{json_path}[{idx}]", findings)


def lint_golden_files(
    *,
    blocking: bool = False,
    extra_paths: list[Path] | None = None,
) -> tuple[bool, list[LiteralFinding]]:
    findings: list[LiteralFinding] = []
    paths = list(iter_golden_json_files())
    if extra_paths:
        paths.extend(extra_paths)

    seen: set[Path] = set()
    for file_path in paths:
        resolved = file_path.resolve()
        if resolved in seen or not file_path.is_file():
            continue
        seen.add(resolved)
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        display = str(file_path)
        _scan_value(data, display, "", findings)

    if blocking:
        ok = len(findings) == 0
    else:
        ok = True
    return ok, findings


def lint_blocking_enabled() -> bool:
    return os.environ.get("GOLDEN_LITERAL_LINT_BLOCKING", "").lower() in (
        "1",
        "true",
        "yes",
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Lint goldens for demo-specific literals")
    parser.add_argument(
        "--blocking",
        action="store_true",
        help="Exit non-zero on findings (default: warnings only unless GOLDEN_LITERAL_LINT_BLOCKING)",
    )
    args = parser.parse_args()
    blocking = args.blocking or lint_blocking_enabled()
    ok, findings = lint_golden_files(blocking=blocking)
    if not findings:
        print("Golden literal lint: OK (no demo literals found)")
        return 0
    for finding in findings[:50]:
        print(f"  [{finding.severity}] {finding.path}: {finding.message}")
    if len(findings) > 50:
        print(f"  … and {len(findings) - 50} more")
    print(f"Golden literal lint: {len(findings)} finding(s)")
    if not ok:
        return 1
    print(
        "(non-blocking — export GOLDEN_LITERAL_LINT_BLOCKING=true or pass --blocking after cleanup)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
