"""
SGRC Tier 1 semantic comparison for error-class GraphQL responses.

Cross-language backends (Go, Node, Rust) need not match Python Saleor's
stacktrace, locations, or extensions.cost — only message semantics and data shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.response_contract import CONTRACT_BUSINESS_ERROR, CONTRACT_SUCCESS
from app.services.response_normalize import normalize_error_message

INVALID_ID_RE = re.compile(
    r"invalid id:.*expected:",
    re.I,
)


@dataclass
class SemanticMatchResult:
    tier1_match: bool
    tier2_match: bool
    client_parity_notes: list[str]
    diff_summary: str | None = None


def _root_field_from_input(input_sent: str | None, endpoint_name: str) -> str | None:
    """Best-effort root field name from probe input or endpoint name."""
    if input_sent:
        m = re.search(r"(?:query|mutation)\s*\{\s*(\w+)", input_sent, re.I)
        if m:
            return m.group(1)
    return endpoint_name


def _normalize_message_category(msg: str) -> str:
    lower = msg.lower()
    if INVALID_ID_RE.search(lower) or "invalid id" in lower:
        return "<invalid_id>"
    return normalize_error_message(msg)


def _first_error(resp: dict[str, Any]) -> dict[str, Any] | None:
    errors = resp.get("errors") or []
    if errors and isinstance(errors[0], dict):
        return errors[0]
    return None


def _data_root_value(resp: dict[str, Any], root_field: str | None) -> Any:
    if not root_field:
        return None
    data = resp.get("data")
    if not isinstance(data, dict):
        return None
    return data.get(root_field)


def _mutation_has_errors(resp: dict[str, Any], root_field: str | None) -> bool | None:
    if not root_field:
        return None
    data = resp.get("data")
    if not isinstance(data, dict):
        return None
    payload = data.get(root_field)
    if not isinstance(payload, dict):
        return None
    errs = payload.get("errors")
    if errs is None:
        return None
    return isinstance(errs, list) and len(errs) > 0


def _extract_error_path(err: dict[str, Any] | None) -> list[str | int] | None:
    if not err:
        return None
    path = err.get("path")
    if isinstance(path, list):
        return path
    return None


def _extract_error_code(err: dict[str, Any] | None) -> str | None:
    if not err:
        return None
    ext = err.get("extensions")
    if not isinstance(ext, dict):
        return None
    exc = ext.get("exception")
    if isinstance(exc, dict) and exc.get("code"):
        return str(exc["code"])
    if ext.get("code"):
        return str(ext["code"])
    return None


def _compare_data_semantics(
    golden_resp: dict[str, Any],
    actual_resp: dict[str, Any],
    *,
    root_field: str | None,
    golden_contract: str,
    endpoint_kind: str,
) -> tuple[bool, str | None]:
    if golden_contract == CONTRACT_SUCCESS:
        return True, None

    g_root = _data_root_value(golden_resp, root_field)
    a_root = _data_root_value(actual_resp, root_field)

    if endpoint_kind == "MUTATION" and golden_contract == CONTRACT_BUSINESS_ERROR:
        g_has = _mutation_has_errors(golden_resp, root_field)
        a_has = _mutation_has_errors(actual_resp, root_field)
        if g_has is not None and a_has is not None:
            if g_has == a_has:
                return True, None
            return False, "Mutation business error payload shape differs"

    if g_root is None and a_root is None:
        return True, None

    if g_root is None or a_root is None:
        if g_root is None and a_root is None:
            return True, None
        return False, f"data.{root_field} nullability differs"

    if (g_root is None) != (a_root is None):
        return False, f"data.{root_field} expected null={g_root is None}, got null={a_root is None}"

    return True, None


def _tier2_requirements(profile: dict[str, Any], g_err: dict[str, Any] | None) -> tuple[bool, bool, list | None, str | None]:
    tier2 = profile.get("tier2") or {}
    requires_path = tier2.get("requires_path")
    if requires_path is None:
        requires_path = bool(profile.get("optional_path") or _extract_error_path(g_err))
    expected_path = tier2.get("expected_path") or profile.get("optional_path") or _extract_error_path(g_err)

    requires_code = tier2.get("requires_code")
    g_code = _extract_error_code(g_err)
    if requires_code is None:
        requires_code = bool(g_code)
    expected_code = tier2.get("expected_code") or g_code
    return requires_path, requires_code, expected_path, expected_code


def compare_semantic_error(
    golden_resp: dict[str, Any],
    actual_resp: dict[str, Any],
    *,
    golden_contract: str,
    endpoint_name: str,
    endpoint_kind: str,
    input_sent: str | None = None,
    semantic_profile: dict[str, Any] | None = None,
    tier2_required: bool = False,
) -> SemanticMatchResult:
    """SGRC Tier 1 + Tier 2 parity for non-success contracts."""
    profile = semantic_profile or {}
    root_field = profile.get("data_path") or _root_field_from_input(input_sent, endpoint_name)

    g_err = _first_error(golden_resp)
    a_err = _first_error(actual_resp)

    g_msg = (g_err or {}).get("message", "")
    a_msg = (a_err or {}).get("message", "")

    if not isinstance(g_msg, str):
        g_msg = str(g_msg)
    if not isinstance(a_msg, str):
        a_msg = str(a_msg)

    g_cat = profile.get("message_pattern") or _normalize_message_category(g_msg)
    a_cat = _normalize_message_category(a_msg)

    if g_cat != a_cat and g_msg.strip() != a_msg.strip():
        return SemanticMatchResult(
            tier1_match=False,
            tier2_match=False,
            client_parity_notes=[],
            diff_summary=f"Message mismatch: expected {g_cat!r}, got {a_cat!r}",
        )

    data_ok, data_diff = _compare_data_semantics(
        golden_resp,
        actual_resp,
        root_field=root_field,
        golden_contract=golden_contract,
        endpoint_kind=endpoint_kind,
    )
    if not data_ok:
        return SemanticMatchResult(
            tier1_match=False,
            tier2_match=False,
            client_parity_notes=[],
            diff_summary=data_diff or "Data semantics differ",
        )

    parity_notes: list[str] = []
    requires_path, requires_code, expected_path, expected_code = _tier2_requirements(profile, g_err)
    actual_path = _extract_error_path(a_err)
    if requires_path and expected_path:
        if actual_path != expected_path:
            parity_notes.append(
                f"Tier 2: errors[].path expected {expected_path}, got {actual_path}"
            )
        elif not actual_path:
            parity_notes.append(
                f"Tier 2: missing errors[].path (required {expected_path})"
            )

    a_code = _extract_error_code(a_err)
    if requires_code and expected_code:
        if a_code != expected_code:
            parity_notes.append(f"Tier 2: error code expected {expected_code!r}, got {a_code!r}")
        elif not a_code:
            parity_notes.append(f"Tier 2: missing error code (required {expected_code!r})")

    tier2_match = len(parity_notes) == 0
    diff = "; ".join(parity_notes) if parity_notes else None
    if tier2_required and parity_notes:
        return SemanticMatchResult(
            tier1_match=True,
            tier2_match=False,
            client_parity_notes=parity_notes,
            diff_summary=diff,
        )
    return SemanticMatchResult(
        tier1_match=True,
        tier2_match=tier2_match,
        client_parity_notes=parity_notes,
        diff_summary=diff,
    )


def build_semantic_profile(
    *,
    golden_response: dict[str, Any],
    golden_contract: str,
    input_sent: str,
    endpoint_name: str,
) -> dict[str, Any] | None:
    """Derive SGRC semantic profile from a golden probe response."""
    import re

    if golden_contract == CONTRACT_SUCCESS:
        return None

    errors = golden_response.get("errors") or []
    err = errors[0] if errors else {}
    msg = err.get("message", "") if isinstance(err, dict) else ""
    if isinstance(msg, str) and "invalid id" in msg.lower():
        message_pattern = "<invalid_id>"
    else:
        message_pattern = normalize_error_message(str(msg)) if msg else None

    m = re.search(r"(?:query|mutation)\s*\{\s*(\w+)", input_sent, re.I)
    root = m.group(1) if m else endpoint_name
    data_root = (golden_response.get("data") or {}).get(root) if isinstance(
        golden_response.get("data"), dict
    ) else None
    optional_path = err.get("path") if isinstance(err, dict) else None

    profile: dict[str, Any] = {
        "contract": golden_contract,
        "data_path": root,
        "expected_null": data_root is None,
    }
    if message_pattern:
        profile["message_pattern"] = message_pattern
    if optional_path:
        profile["optional_path"] = optional_path
        profile["tier2"] = {
            "requires_path": True,
            "expected_path": optional_path,
            "requires_code": bool(_extract_error_code(err if isinstance(err, dict) else None)),
            "expected_code": _extract_error_code(err if isinstance(err, dict) else None),
        }
    return profile


def is_error_contract(contract: str) -> bool:
    return contract != CONTRACT_SUCCESS
