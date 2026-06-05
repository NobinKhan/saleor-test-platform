"""Golden reference comparison tests."""

import json

from app.services.reference_corpus import GoldenProbe, write_corpus
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
    assert result.expected_response is None


def test_compare_match(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="products",
        endpoint_kind="QUERY",
        category="products",
        input_sent="query { products(first: 1) { edges { node { id } } } }",
        golden_response={"data": {"products": {"edges": []}}, "errors": None},
        golden_outcome="success_with_data",
        golden_status="pass",
        error_pattern=None,
        response_shape_hash="sha256:abc",
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    monkeypatch.setattr(
        "app.services.reference_corpus.response_shape_hash",
        lambda r: "sha256:abc",
    )
    actual = {"data": {"products": {"edges": []}}}
    result = compare_to_golden(
        "3.23.7",
        "products",
        "QUERY",
        actual,
        {"outcome": "success_with_data", "status": "pass"},
    )
    assert result.match_status == "match"
    assert result.recommended_status == "pass"
    assert "products" in (result.expected_response or "")


def test_compare_outcome_mismatch(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="webhook",
        endpoint_kind="QUERY",
        category="webhooks",
        input_sent='query { webhook(id: "x") { id } }',
        golden_response={"errors": [{"message": "required"}]},
        golden_outcome="schema_error",
        golden_status="fail",
        error_pattern=None,
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
        {"errors": [{"message": "required"}]},
        {"outcome": "validation_error", "status": "warn"},
    )
    assert result.match_status == "mismatch"
    assert "validation_error" in (result.diff_summary or "")
