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
    missing_l3 = schema_diff.get("missing_l3_fields") or []
    client_l3_pass = schema_diff.get("client_schema_gate_pass", True)
    version_warn = schema_diff.get("version_warning") or ""
    intro_err = schema_diff.get("introspection_error")
    gate_source = schema_diff.get("schema_gate_source") or "dashboard catalog"
    source_label = "golden schema" if gate_source == "golden" else "dashboard catalog"

    issues: list[str] = list(schema_diff.get("schema_issues") or [])
    if intro_err:
        issues.append(f"Introspection failed: {intro_err}")
    if missing_q:
        issues.append(f"{len(missing_q)} {source_label} queries missing on target")
    if missing_m:
        issues.append(f"{len(missing_m)} {source_label} mutations missing on target")
    if missing_l3:
        issues.append(f"{len(missing_l3)} L3 bundle root field(s) missing on target")
    if version_warn and "major" in version_warn.lower():
        issues.append(version_warn)

    gate_pass = (
        not intro_err
        and not missing_q
        and not missing_m
        and client_l3_pass
        and not (version_warn and "major" in version_warn.lower())
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
    min_compat: float = 100.0,
    tier2_pass: bool = True,
    parity_gaps: int = 0,
) -> bool:
    if not schema_gate_pass or compatibility_score is None:
        return False
    if parity_gaps > 0 or not tier2_pass:
        return False
    return compatibility_score >= min_compat
