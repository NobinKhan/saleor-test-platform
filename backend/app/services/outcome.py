"""
Classify GraphQL probe outcomes for dashboard compatibility reporting.
"""

from __future__ import annotations

from typing import Any


def _msg_matches_schema_error(msg: str) -> bool:
    lower = msg.lower()
    schema_markers = (
        "cannot query",
        "undefined type",
        "field has unsupported",
        "unknown type",
        "fieldundefined",
        "unknown field",
        "did you mean",
        "field undefined",
    )
    if any(m in lower for m in schema_markers):
        return True
    if "argument" in lower and "required but not provided" in lower:
        return True
    if "argument" in lower and "is required" in lower:
        return True
    return False


def classify_graphql_response(
    resp_json: dict[str, Any],
    *,
    http_status: int,
    endpoint_kind: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    Return outcome metadata for a single endpoint probe.
    Maps to pass/fail/warn via test_runner status rules.
    """
    errors = resp_json.get("errors") or []
    data = resp_json.get("data")
    has_graphql_data = bool(data) and data is not None
    response_valid = http_status == 200 and not errors and has_graphql_data

    if http_status != 200:
        return {
            "outcome": "http_error",
            "response_valid": False,
            "has_graphql_data": False,
            "expected": f"Expect HTTP 200, got {http_status}",
            "status": "fail",
            "error_message": error_message or f"HTTP {http_status}",
        }

    if not errors:
        return {
            "outcome": "success_with_data",
            "response_valid": True,
            "has_graphql_data": True,
            "expected": "Expect GraphQL 200 with data and no errors",
            "status": "pass",
            "error_message": None,
        }

    first_err = errors[0] if errors else {}
    msg = first_err.get("message", "")
    ext = first_err.get("extensions", {})
    code = ext.get("code", "")

    auth_codes = {
        "permission",
        "authentication",
        "forbidden",
        "jwt-error",
        "jwt-invalid",
        "PERMISSION_DENIED",
    }
    validation_codes = {
        "INVALID",
        "GRAPHQL_VALIDATION_FAILED",
        "REQUIRED",
        "UNIQUE",
    }

    if code in auth_codes or str(code).lower() in auth_codes:
        return {
            "outcome": "auth_denied",
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Expect staff access or acceptable permission denial",
            "status": "warn",
            "error_message": msg,
        }
    if _msg_matches_schema_error(msg):
        return {
            "outcome": "schema_error",
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Expect operation and fields to exist in API schema",
            "status": "fail",
            "error_message": msg,
        }
    if "not found" in msg.lower() or "does not exist" in msg.lower():
        return {
            "outcome": "not_found_probe",
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Probe uses placeholder IDs — not-found is acceptable",
            "status": "pass",
            "error_message": None,
        }
    if code in validation_codes:
        return {
            "outcome": "validation_error",
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Mutation probe uses minimal/dummy input — validation errors are expected",
            "status": "warn",
            "error_message": msg,
        }
    if endpoint_kind == "MUTATION":
        return {
            "outcome": "validation_error",
            "response_valid": False,
            "has_graphql_data": has_graphql_data,
            "expected": "Mutation probe uses minimal/dummy input — validation errors are expected",
            "status": "warn",
            "error_message": msg,
        }

    return {
        "outcome": "unexpected_error",
        "response_valid": False,
        "has_graphql_data": has_graphql_data,
        "expected": "Expect GraphQL data or a known error pattern",
        "status": "warn",
        "error_message": msg,
    }


def classify_transport_error(
    *,
    kind: str,
    message: str,
) -> dict[str, Any]:
    outcome = "timeout" if "timeout" in message.lower() else "transport_error"
    return {
        "outcome": outcome,
        "response_valid": False,
        "has_graphql_data": False,
        "expected": "Expect reachable GraphQL endpoint",
        "status": "fail",
        "error_message": message,
    }
