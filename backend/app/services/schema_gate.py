"""
Schema compatibility gate — separate from behavioral golden comparison.
"""

from __future__ import annotations

from typing import Any


def compute_schema_gate(schema_diff: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate whether the target passes the schema/catalog gate."""
    if not schema_diff:
        return {
            "schema_gate_pass": True,
            "missing_queries": 0,
            "missing_mutations": 0,
            "schema_score": 100.0,
            "schema_issues": [],
        }

    missing_q = schema_diff.get("missing_queries") or []
    missing_m = schema_diff.get("missing_mutations") or []
    version_warn = schema_diff.get("version_warning") or ""
    intro_err = schema_diff.get("introspection_error")
    gate_source = schema_diff.get("schema_gate_source") or "dashboard catalog"
    source_label = "golden schema" if gate_source == "golden" else "dashboard catalog"

    issues: list[str] = []
    if intro_err:
        issues.append(f"Introspection failed: {intro_err}")
    if missing_q:
        issues.append(f"{len(missing_q)} {source_label} queries missing on target")
    if missing_m:
        issues.append(f"{len(missing_m)} {source_label} mutations missing on target")
    if version_warn and "major" in version_warn.lower():
        issues.append(version_warn)

    gate_pass = not intro_err and not missing_q and not missing_m and not (
        version_warn and "major" in version_warn.lower()
    )

    total_missing = len(missing_q) + len(missing_m)
    schema_score = 100.0 if gate_pass else max(0.0, 100.0 - total_missing * 2)

    return {
        "schema_gate_pass": gate_pass,
        "missing_queries": len(missing_q),
        "missing_mutations": len(missing_m),
        "schema_score": round(schema_score, 1),
        "schema_issues": issues,
        "schema_gate_source": gate_source,
    }


def compute_certified(
    *,
    schema_gate_pass: bool,
    compatibility_score: float | None,
    min_compat: float = 95.0,
) -> bool:
    if not schema_gate_pass or compatibility_score is None:
        return False
    return compatibility_score >= min_compat
