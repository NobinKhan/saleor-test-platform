"""
Classify GraphQL probe outcomes for dashboard compatibility reporting.
"""

from __future__ import annotations

from typing import Any

from app.services.response_contract import (
    CONTRACT_BUSINESS_ERROR,
    CONTRACT_GRAPHQL_ERROR,
    CONTRACT_SUCCESS,
    CONTRACT_TRANSPORT_ERROR,
    classify_response_contract,
    contract_to_legacy_outcome,
)


def classify_graphql_response(
    resp_json: dict[str, Any],
    *,
    http_status: int,
    endpoint_kind: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    Return outcome metadata for a single endpoint probe.
    Uses HTTP-agnostic response contract classification.
    """
    contract = classify_response_contract(resp_json, http_status=http_status)
    outcome = contract_to_legacy_outcome(contract)
    errors = resp_json.get("errors") or []
    data = resp_json.get("data")
    has_graphql_data = bool(data) and data is not None
    first_msg = errors[0].get("message", "") if errors else None

    if contract == CONTRACT_SUCCESS:
        return {
            "outcome": outcome,
            "response_contract": contract,
            "response_valid": True,
            "has_graphql_data": True,
            "expected": "Expect GraphQL success response",
            "status": "pass",
            "error_message": None,
        }

    if contract == CONTRACT_TRANSPORT_ERROR:
        return {
            "outcome": outcome,
            "response_contract": contract,
            "response_valid": False,
            "has_graphql_data": False,
            "expected": f"Expect valid GraphQL response, got HTTP {http_status}",
            "status": "fail",
            "error_message": error_message or first_msg or f"HTTP {http_status}",
        }

    errors = resp_json.get("errors") or []
    first_msg = errors[0].get("message", "") if errors else None
    if contract == CONTRACT_BUSINESS_ERROR or (
        endpoint_kind == "MUTATION"
        and errors
        and (errors[0].get("extensions") or {}).get("code") == "INVALID"
    ):
        return {
            "outcome": "validation_error",
            "response_contract": contract,
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Expect business-level validation error in data.errors",
            "status": "warn",
            "error_message": first_msg,
        }

    if contract == CONTRACT_GRAPHQL_ERROR:
        lower = (first_msg or "").lower()
        schema_markers = (
            "field", "argument", "type", "query", "mutation", "required", "unknown",
        )
        if any(m in lower for m in schema_markers):
            resolved_outcome = "schema_error"
            resolved_status = "fail"
        else:
            resolved_outcome = "unexpected_error"
            resolved_status = "warn"
        return {
            "outcome": resolved_outcome,
            "response_contract": contract,
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Expect GraphQL validation error for probe input",
            "status": resolved_status,
            "error_message": first_msg,
        }

    status = "warn"
    expected_map = {
        "business_error": "Expect business-level validation error in data.errors",
        "graphql_error": "Expect GraphQL validation error for probe input",
        "auth_error": "Expect auth/permission denial for probe",
        "not_found": "Expect not-found for placeholder probe ID",
    }
    return {
        "outcome": outcome,
        "response_contract": contract,
        "response_valid": False,
        "has_graphql_data": has_graphql_data,
        "expected": expected_map.get(contract, "Expect known error pattern"),
        "status": status,
        "error_message": first_msg,
    }


def classify_transport_error(
    *,
    kind: str,
    message: str,
) -> dict[str, Any]:
    outcome = "timeout" if "timeout" in message.lower() else "transport_error"
    return {
        "outcome": outcome,
        "response_contract": CONTRACT_TRANSPORT_ERROR,
        "response_valid": False,
        "has_graphql_data": False,
        "expected": "Expect reachable GraphQL endpoint",
        "status": "fail",
        "error_message": message,
    }
