"""
Input binding checks — validate success responses echo input values.

Ensures that mutation success responses contain the input values sent,
proving the backend is computing responses, not serving canned JSON.
"""

from __future__ import annotations

from typing import Any


def check_input_bindings(
    response: dict[str, Any],
    variables: dict[str, Any],
    binding_rules: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Check that response fields echo the input variables.

    Args:
        response: The GraphQL response dict
        variables: The variables sent with the request
        binding_rules: List of binding rules, each with:
            - field: JSON path to check in response (e.g. "data.productCreate.product.name")
            - expected_input: Key in variables to match against
            - Optional transform: "relay_id" to decode relay global ID

    Returns:
        (passes, list_of_failure_messages)
    """
    failures: list[str] = []

    for rule in binding_rules:
        field_path = rule.get("field", "")
        expected_key = rule.get("expected_input", "")

        if not field_path or not expected_key:
            continue

        actual_value = _resolve_json_path(response, field_path)
        expected_value = _extract_expected_value(variables, expected_key)

        if actual_value is None:
            failures.append(
                f"Binding check: field '{field_path}' not found in response"
            )
            continue

        if expected_value is None:
            failures.append(
                f"Binding check: expected input key '{expected_key}' not found in variables"
            )
            continue

        if isinstance(expected_value, dict):
            expected_str = str(expected_value.get("id", expected_value))
        else:
            expected_str = str(expected_value)

        if isinstance(actual_value, dict):
            actual_str = str(actual_value.get("id", actual_value))
        else:
            actual_str = str(actual_value)

        if expected_str and actual_str and expected_str != actual_str:
            failures.append(
                f"Binding check failed: {field_path} = '{actual_str}' "
                f"does not match input {expected_key} = '{expected_str}'"
            )

    return len(failures) == 0, failures


def _resolve_json_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated JSON path like 'data.product.name'."""
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def _extract_expected_value(
    variables: dict[str, Any],
    key: str,
) -> Any:
    """Extract expected value from variables, handling nested input objects."""
    val = variables.get(key)
    if val is not None:
        return val

    if "." in key:
        parts = key.split(".")
        current: Any = variables
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    return None


BINDING_RULES: dict[str, list[dict[str, Any]]] = {
    "productCreate": [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
        {"field": "data.productCreate.product.slug", "expected_input": "input.slug"},
    ],
    "categoryCreate": [
        {"field": "data.categoryCreate.category.name", "expected_input": "input.name"},
        {"field": "data.categoryCreate.category.slug", "expected_input": "input.slug"},
    ],
    "collectionCreate": [
        {"field": "data.collectionCreate.collection.name", "expected_input": "input.name"},
        {"field": "data.collectionCreate.collection.slug", "expected_input": "input.slug"},
    ],
}


def get_binding_rules(operation_name: str) -> list[dict[str, Any]]:
    """Get binding rules for a known operation."""
    return BINDING_RULES.get(operation_name, [])
