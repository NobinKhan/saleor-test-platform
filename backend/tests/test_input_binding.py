"""Input binding tests."""

from app.services.input_binding import (
    check_input_bindings,
    _resolve_json_path,
    _extract_expected_value,
    get_binding_rules,
)


def test_resolve_json_path_simple():
    data = {"data": {"product": {"name": "Test"}}}
    assert _resolve_json_path(data, "data.product.name") == "Test"


def test_resolve_json_path_missing():
    data = {"data": {}}
    assert _resolve_json_path(data, "data.product.name") is None


def test_resolve_json_path_list():
    data = {"data": {"edges": [{"node": {"id": "1"}}]}}
    assert _resolve_json_path(data, "data.edges.0.node.id") == "1"


def test_extract_expected_value_top_level():
    variables = {"input": {"name": "Test"}}
    assert _extract_expected_value(variables, "input") == {"name": "Test"}


def test_extract_expected_value_nested():
    variables = {"input": {"name": "Test"}}
    assert _extract_expected_value(variables, "input.name") == "Test"


def test_extract_expected_value_missing():
    variables = {"input": {"name": "Test"}}
    assert _extract_expected_value(variables, "input.slug") is None


def test_input_binding_passes():
    response = {"data": {"productCreate": {"product": {"name": "My Product", "slug": "my-product"}}}}
    variables = {"input": {"name": "My Product", "slug": "my-product"}}
    rules = [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
        {"field": "data.productCreate.product.slug", "expected_input": "input.slug"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert passes
    assert failures == []


def test_input_binding_fails():
    response = {"data": {"productCreate": {"product": {"name": "Wrong", "slug": "wrong"}}}}
    variables = {"input": {"name": "Expected", "slug": "expected"}}
    rules = [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert not passes
    assert any("does not match" in f for f in failures)


def test_input_binding_field_missing():
    response = {"data": {}}
    variables = {"input": {"name": "Test"}}
    rules = [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert not passes
    assert any("not found in response" in f for f in failures)


def test_input_binding_variable_missing():
    response = {"data": {"productCreate": {"product": {"name": "Test"}}}}
    variables = {}
    rules = [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert not passes
    assert any("not found in variables" in f for f in failures)


def test_get_binding_rules_known():
    rules = get_binding_rules("productCreate")
    assert len(rules) >= 2
    assert rules[0]["field"] == "data.productCreate.product.name"


def test_get_binding_rules_unknown():
    rules = get_binding_rules("unknownOperation")
    assert rules == []


def test_input_binding_dict_values():
    response = {"data": {"productCreate": {"product": {"name": "Test"}}}}
    variables = {"input": {"name": "Test"}}
    rules = [
        {"field": "data.productCreate.product.name", "expected_input": "input.name"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert passes


def test_input_binding_nested_input_dict():
    response = {"data": {"productCreate": {"product": {"id": "UHJvZHVjdDox"}}}}
    variables = {"input": {}}
    rules = [
        {"field": "data.productCreate.product.id", "expected_input": "input.id"},
    ]
    passes, failures = check_input_bindings(response, variables, rules)
    assert not passes
    assert any("not found in variables" in f for f in failures)
