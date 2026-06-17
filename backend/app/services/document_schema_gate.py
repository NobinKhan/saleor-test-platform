"""
Deep L3 document schema gate — validate client GraphQL documents against target introspection.
"""

from __future__ import annotations

from typing import Any

from graphql import GraphQLError, build_client_schema, parse, validate

from app.services.client_bundles import ClientBundle
from app.services.introspection import introspect_full_schema
from app.services.semantic_compare import is_error_contract


def _introspection_data_for_build(introspection_result: dict[str, Any]) -> dict[str, Any]:
    """Extract the introspection ``data`` object for ``build_client_schema``."""
    if isinstance(introspection_result, dict) and "data" in introspection_result:
        inner = introspection_result["data"]
        if isinstance(inner, dict) and "__schema" in inner:
            return inner
    if isinstance(introspection_result, dict) and "__schema" in introspection_result:
        return introspection_result
    return introspection_result


def validate_document_against_schema(
    document: str,
    introspection_result: dict[str, Any],
) -> list[dict[str, str]]:
    """Return validation issues for a GraphQL document against a full introspection schema."""
    issues: list[dict[str, str]] = []
    schema_input = _introspection_data_for_build(introspection_result)
    try:
        client_schema = build_client_schema(schema_input)
    except Exception as exc:
        return [{"field": "", "kind": "", "reason": f"schema_build_error: {exc}"}]

    try:
        doc_ast = parse(document)
    except GraphQLError as exc:
        return [{"field": "", "kind": "", "reason": f"parse_error: {exc.message}"}]
    except Exception as exc:
        return [{"field": "", "kind": "", "reason": f"parse_error: {exc}"}]

    for error in validate(client_schema, doc_ast):
        issues.append({
            "field": "",
            "kind": "",
            "reason": error.message,
        })
    return issues


def compute_document_schema_gate(
    bundles: list[ClientBundle],
    introspection_result: dict[str, Any] | None,
    *,
    recorded_only: bool = True,
) -> dict[str, Any]:
    """Validate each bundle document against full target schema (nested fields + argument types)."""
    missing: list[dict[str, str]] = []
    if not introspection_result:
        return {
            "document_schema_gate_pass": True,
            "missing_document_fields": [],
            "checked_bundles": 0,
            "skipped": True,
        }

    checked = 0
    for bundle in bundles:
        if recorded_only and not bundle.has_golden():
            continue
        if bundle.golden_contract and is_error_contract(bundle.golden_contract):
            continue
        checked += 1
        doc_issues = validate_document_against_schema(bundle.document, introspection_result)
        for issue in doc_issues:
            missing.append({
                "bundle_id": bundle.bundle_id,
                "field": issue.get("field") or "",
                "kind": issue.get("kind") or "",
                "reason": issue.get("reason") or "validation_error",
            })

    return {
        "document_schema_gate_pass": len(missing) == 0,
        "missing_document_fields": missing,
        "checked_bundles": checked,
        "skipped": False,
    }


def merge_document_schema_into_diff(
    schema_diff: dict[str, Any],
    document_gate: dict[str, Any],
) -> dict[str, Any]:
    """Attach deep document schema gate results to a schema_diff payload."""
    merged = dict(schema_diff)
    merged["document_schema_gate_pass"] = document_gate.get("document_schema_gate_pass", True)
    merged["missing_document_fields"] = document_gate.get("missing_document_fields") or []
    merged["document_schema_gate_checked"] = document_gate.get("checked_bundles", 0)
    if not document_gate.get("document_schema_gate_pass", True):
        count = len(document_gate.get("missing_document_fields") or [])
        merged.setdefault("schema_gate_source", "golden + L3 bundles")
        issues = merged.get("schema_issues") or []
        if not isinstance(issues, list):
            issues = []
        issues.append(f"{count} L3 document validation issue(s) on target schema")
        merged["schema_issues"] = issues
    return merged


async def fetch_and_validate_bundles(
    bundles: list[ClientBundle],
    *,
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    recorded_only: bool = True,
) -> dict[str, Any]:
    """Fetch full introspection from target and run document schema gate."""
    intro = await introspect_full_schema(saleor_url, token, timeout)
    return compute_document_schema_gate(
        bundles, intro, recorded_only=recorded_only
    )
