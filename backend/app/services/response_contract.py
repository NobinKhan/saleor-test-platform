"""
HTTP-agnostic GraphQL response contract classification.

Maps any Saleor GraphQL response to a semantic class (success, business_error, etc.)
independent of HTTP status code when the body contains valid GraphQL JSON.
"""

from __future__ import annotations

from typing import Any

CONTRACT_SUCCESS = "success"
CONTRACT_BUSINESS_ERROR = "business_error"
CONTRACT_GRAPHQL_ERROR = "graphql_error"
CONTRACT_AUTH_ERROR = "auth_error"
CONTRACT_NOT_FOUND = "not_found"
CONTRACT_TRANSPORT_ERROR = "transport_error"

AUTH_CODES = frozenset({
    "permission", "authentication", "forbidden", "jwt-error", "jwt-invalid",
    "PERMISSION_DENIED", "InvalidTokenError",
})
NOT_FOUND_MARKERS = ("not found", "does not exist", "invalid id", "couldn't resolve")


def _first_top_error(resp: dict[str, Any]) -> tuple[str, str]:
    errors = resp.get("errors") or []
    if not errors:
        return "", ""
    err = errors[0]
    msg = err.get("message", "")
    ext = err.get("extensions") or {}
    code = ""
    if isinstance(ext.get("exception"), dict):
        code = ext["exception"].get("code", "") or ""
    code = code or ext.get("code", "") or ""
    return msg, str(code)


def _has_business_errors(resp: dict[str, Any]) -> bool:
    data = resp.get("data")
    if not isinstance(data, dict):
        return False
    for val in data.values():
        if isinstance(val, dict) and val.get("errors"):
            return True
    return False


def _msg_is_not_found(msg: str) -> bool:
    lower = msg.lower()
    return any(m in lower for m in NOT_FOUND_MARKERS)


def _msg_is_auth(msg: str, code: str) -> bool:
    if code in ("InvalidTokenError", "jwt-error", "jwt-invalid"):
        return True
    if code in AUTH_CODES and code not in ("PERMISSION_DENIED", "PermissionDenied"):
        return True
    lower = msg.lower()
    if "invalid token" in lower:
        return True
    if "sign in" in lower or "log in" in lower:
        return True
    if "authenticate" in lower and "permission" not in lower:
        return True
    return False


def classify_response_contract(
    resp_json: dict[str, Any] | None,
    *,
    http_status: int,
) -> str:
    """Classify a GraphQL response into a semantic contract class."""
    if resp_json is None:
        return CONTRACT_TRANSPORT_ERROR

    errors = resp_json.get("errors") or []
    data = resp_json.get("data")
    has_data = data is not None and data != {}

    if errors:
        msg, code = _first_top_error(resp_json)
        if _msg_is_auth(msg, code):
            return CONTRACT_AUTH_ERROR
        if _msg_is_not_found(msg):
            return CONTRACT_NOT_FOUND
        return CONTRACT_GRAPHQL_ERROR

    if _has_business_errors(resp_json):
        return CONTRACT_BUSINESS_ERROR

    if has_data:
        return CONTRACT_SUCCESS

    if http_status != 200:
        return CONTRACT_TRANSPORT_ERROR

    return CONTRACT_GRAPHQL_ERROR


def infer_probe_stability(contract: str, endpoint_kind: str) -> str:
    """Tag whether a probe is safe to compare across DB instances."""
    if contract in (CONTRACT_GRAPHQL_ERROR, CONTRACT_BUSINESS_ERROR, CONTRACT_AUTH_ERROR, CONTRACT_NOT_FOUND):
        return "stateless"
    if contract == CONTRACT_SUCCESS and endpoint_kind == "QUERY":
        return "stateful"
    if contract == CONTRACT_SUCCESS and endpoint_kind == "MUTATION":
        return "stateful"
    return "stateless"


def contract_to_status(contract: str, *, compatible: bool) -> str:
    """Map contract + compatibility to test result status."""
    if not compatible:
        return "fail"
    return "pass"


def contract_family(contract: str) -> str:
    """Coarse bucket for compatibility: success, rejection (any invalid), not_found, transport."""
    if contract == CONTRACT_SUCCESS:
        return "success"
    if contract == CONTRACT_NOT_FOUND:
        return "not_found"
    if contract == CONTRACT_TRANSPORT_ERROR:
        return "transport"
    if contract in (CONTRACT_BUSINESS_ERROR, CONTRACT_GRAPHQL_ERROR, CONTRACT_AUTH_ERROR):
        return "rejection"
    return "rejection"


def contract_to_legacy_outcome(contract: str) -> str:
    """Map contract to outcome string stored on TestResult."""
    mapping = {
        CONTRACT_SUCCESS: "success_with_data",
        CONTRACT_BUSINESS_ERROR: "validation_error",
        CONTRACT_GRAPHQL_ERROR: "schema_error",
        CONTRACT_AUTH_ERROR: "auth_denied",
        CONTRACT_NOT_FOUND: "not_found_probe",
        CONTRACT_TRANSPORT_ERROR: "transport_error",
    }
    return mapping.get(contract, "unexpected_error")
