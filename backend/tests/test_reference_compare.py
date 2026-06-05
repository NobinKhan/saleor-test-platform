"""Golden reference comparison tests."""

import json

from app.services.reference_corpus import GoldenProbe
from app.services.reference_compare import compare_to_golden


def test_compare_missing_golden(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: None,
    )
    result = compare_to_golden(
        "3.23.7",
        "unknownEndpoint",
        "QUERY",
        {"data": {"x": 1}},
        {"outcome": "success_with_data", "status": "pass"},
    )
    assert result.match_status == "missing_golden"
    assert not result.compatible


def test_compare_contract_match(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="products",
        endpoint_kind="QUERY",
        category="products",
        input_sent="query { products(first: 1) { edges { node { id } } } }",
        golden_response={"data": {"products": {"edges": []}}},
        golden_outcome="success_with_data",
        golden_status="pass",
        golden_contract="success",
        response_shape_hash="sha256:abc",
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    monkeypatch.setattr(
        "app.services.reference_compare._normalized_hash",
        lambda r: "sha256:abc",
    )
    actual = {"data": {"products": {"edges": []}}}
    result = compare_to_golden(
        "3.23.7",
        "products",
        "QUERY",
        actual,
        {"outcome": "success_with_data", "status": "pass"},
        http_status=200,
    )
    assert result.match_status == "match"
    assert result.compatible
    assert result.recommended_status == "pass"


def test_rejection_family_compatible(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="accountAddressCreate",
        endpoint_kind="MUTATION",
        category="account",
        input_sent="mutation { accountAddressCreate(input: {}) { errors { field message } } }",
        golden_response={"errors": [{"message": "Invalid token"}]},
        golden_outcome="auth_denied",
        golden_status="warn",
        golden_contract="auth_error",
        response_shape_hash=None,
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    actual = {
        "data": {
            "accountAddressCreate": {
                "errors": [{"field": "country", "message": "required"}],
            }
        },
    }
    result = compare_to_golden(
        "3.23.7",
        "accountAddressCreate",
        "MUTATION",
        actual,
        {"outcome": "validation_error", "status": "warn"},
        http_status=200,
    )
    assert result.compatible
    assert result.match_status == "match"


def test_compare_contract_mismatch(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="webhook",
        endpoint_kind="QUERY",
        category="webhooks",
        input_sent='query { webhook(id: "x") { id } }',
        golden_response={"errors": [{"message": "required"}]},
        golden_outcome="schema_error",
        golden_status="fail",
        golden_contract="graphql_error",
        response_shape_hash=None,
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    result = compare_to_golden(
        "3.23.7",
        "webhook",
        "QUERY",
        {"data": {"webhook": None}},
        {"outcome": "success_with_data", "status": "pass"},
        http_status=200,
    )
    assert result.match_status == "mismatch"
    assert not result.compatible
    assert "graphql_error" in (result.diff_summary or "")
