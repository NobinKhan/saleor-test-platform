"""
L3 schema gate — verify Dashboard bundle root fields exist on target schema (no execution).
"""

from __future__ import annotations

from typing import Any

from graphql import parse
from graphql.language.ast import (
    FragmentSpreadNode,
    InlineFragmentNode,
    OperationDefinitionNode,
)

from app.services.client_bundles import ClientBundle
from app.services.dashboard_bundle_import import root_fields_in_document


def compute_client_bundle_schema_gate(
    bundles: list[ClientBundle],
    intro: dict[str, list[str]],
    *,
    recorded_only: bool = True,
) -> dict[str, Any]:
    """Check that each bundle's root GraphQL fields exist on the target API schema."""
    queries = set(intro.get("queries") or [])
    mutations = set(intro.get("mutations") or [])
    missing: list[dict[str, str]] = []

    for bundle in bundles:
        if recorded_only and not bundle.has_golden():
            continue
        try:
            roots = root_fields_in_document(bundle.document)
        except Exception as exc:
            missing.append({
                "bundle_id": bundle.bundle_id,
                "field": "",
                "kind": "",
                "reason": f"parse_error: {exc}",
            })
            continue
        for field_name, kind in roots:
            pool = queries if kind == "QUERY" else mutations
            if field_name not in pool:
                missing.append({
                    "bundle_id": bundle.bundle_id,
                    "field": field_name,
                    "kind": kind,
                })

    return {
        "client_schema_gate_pass": len(missing) == 0,
        "missing_l3_fields": missing,
        "checked_bundles": sum(
            1 for b in bundles if not recorded_only or b.has_golden()
        ),
    }


def merge_client_schema_into_diff(
    schema_diff: dict[str, Any],
    client_gate: dict[str, Any],
) -> dict[str, Any]:
    """Attach L3 schema gate results to a schema_diff payload."""
    merged = dict(schema_diff)
    merged["client_schema_gate_pass"] = client_gate.get("client_schema_gate_pass", True)
    merged["missing_l3_fields"] = client_gate.get("missing_l3_fields") or []
    merged["client_schema_gate_checked"] = client_gate.get("checked_bundles", 0)
    if not client_gate.get("client_schema_gate_pass", True):
        count = len(client_gate.get("missing_l3_fields") or [])
        merged.setdefault("schema_gate_source", "dashboard catalog + L3 bundles")
        issues = merged.get("schema_issues") or []
        if not isinstance(issues, list):
            issues = []
        issues.append(f"{count} L3 bundle root field(s) missing on target schema")
        merged["schema_issues"] = issues
    return merged
