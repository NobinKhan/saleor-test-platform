"""Golden reference comparison tests."""

import json

from app.services.reference_compare import compare_probe_to_actual, compare_to_golden
from app.services.reference_corpus import GoldenProbe


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
        "errors": [{"message": "Invalid token."}],
        "data": {"accountAddressCreate": None},
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


def test_checkout_minimal_response_matches_golden(tmp_path, monkeypatch):
    """Go/Rust backends without stacktrace/locations/path pass SGRC Tier 1."""
    golden_response = {
        "errors": [
            {
                "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Checkout.",
                "locations": [{"line": 1, "column": 9}],
                "path": ["checkout"],
                "extensions": {
                    "exception": {
                        "code": "GraphQLError",
                        "stacktrace": ["Traceback..."],
                    }
                },
            }
        ],
        "data": {"checkout": None},
        "extensions": {"cost": {"requestedQueryCost": 1}},
    }
    golden = GoldenProbe(
        endpoint_name="checkout",
        endpoint_kind="QUERY",
        category="checkout",
        input_sent='query { checkout(id: "00000000-0000-0000-0000-000000000000") { id } }',
        golden_response=golden_response,
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
        response_shape_hash="sha256:e2a19b01f4075db3",
        semantic_profile={
            "contract": "not_found",
            "message_pattern": "<invalid_id>",
            "data_path": "checkout",
            "expected_null": True,
            "optional_path": ["checkout"],
        },
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    actual = {
        "data": {"checkout": None},
        "errors": [
            {
                "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Checkout.",
            }
        ],
    }
    result = compare_to_golden(
        "3.23.7",
        "checkout",
        "QUERY",
        actual,
        {"outcome": "not_found_probe", "status": "warn"},
        http_status=200,
    )
    assert result.compatible
    assert result.match_status in ("match", "parity_gap")
    if result.match_status == "parity_gap":
        assert result.client_parity_note
        assert "path" in (result.client_parity_note or "").lower()
    assert "stacktrace" not in (result.expected_response or "").lower()


def test_expected_response_omits_stacktrace(tmp_path, monkeypatch):
    golden_response = {
        "errors": [
            {
                "message": "Invalid ID: x. Expected: Checkout.",
                "extensions": {"exception": {"stacktrace": ["Traceback..."], "code": "GraphQLError"}},
            }
        ],
        "data": {"checkout": None},
    }
    golden = GoldenProbe(
        endpoint_name="checkout",
        endpoint_kind="QUERY",
        category="checkout",
        input_sent='query { checkout(id: "x") { id } }',
        golden_response=golden_response,
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    result = compare_to_golden(
        "3.23.7",
        "checkout",
        "QUERY",
        {"data": {"checkout": None}, "errors": [{"message": "Invalid ID: x. Expected: Checkout."}]},
        {"outcome": "not_found_probe", "status": "warn"},
    )
    assert "stacktrace" not in (result.expected_response or "").lower()
    assert "GraphQLError" not in (result.expected_response or "")


def test_checkout_wrong_message_mismatch(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="checkout",
        endpoint_kind="QUERY",
        category="checkout",
        input_sent='query { checkout(id: "x") { id } }',
        golden_response={
            "errors": [{"message": "Invalid ID: x. Expected: Checkout."}],
            "data": {"checkout": None},
        },
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    actual = {
        "data": {"checkout": None},
        "errors": [{"message": "Something else went wrong"}],
    }
    result = compare_to_golden(
        "3.23.7",
        "checkout",
        "QUERY",
        actual,
        {"outcome": "not_found_probe", "status": "warn"},
    )
    assert not result.compatible
    assert result.match_status == "mismatch"


def test_golden_stacktrace_actual_without_still_matches(tmp_path, monkeypatch):
    golden = GoldenProbe(
        endpoint_name="checkout",
        endpoint_kind="QUERY",
        category="checkout",
        input_sent='query { checkout(id: "00000000-0000-0000-0000-000000000000") { id } }',
        golden_response={
            "errors": [
                {
                    "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Checkout.",
                    "extensions": {"exception": {"stacktrace": ["long trace"]}},
                }
            ],
            "data": {"checkout": None},
        },
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
    )
    monkeypatch.setattr(
        "app.services.reference_compare.load_probe_from_disk",
        lambda *a, **k: golden,
    )
    actual = {
        "errors": [
            {
                "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Checkout.",
            }
        ],
        "data": {"checkout": None},
    }
    result = compare_to_golden(
        "3.23.7",
        "checkout",
        "QUERY",
        actual,
        {"outcome": "not_found_probe", "status": "warn"},
    )
    assert result.compatible
    assert result.match_status in ("match", "parity_gap")


def test_tier2_gate_fails_on_missing_client_code(tmp_path):
    golden = GoldenProbe(
        endpoint_name="order",
        endpoint_kind="QUERY",
        category="orders",
        input_sent='query { order(id: "x") { id } }',
        golden_response={
            "errors": [
                {
                    "message": "Order not found.",
                    "extensions": {"code": "NOT_FOUND"},
                }
            ],
            "data": {"order": None},
        },
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
        semantic_profile={
            "tier2": {"requires_code": True, "expected_code": "NOT_FOUND"},
        },
    )
    actual = {
        "data": {"order": None},
        "errors": [{"message": "Order not found."}],
    }
    result = compare_probe_to_actual(
        golden,
        actual,
        tier2_required=True,
    )
    assert result.match_status == "tier2_fail"
    assert not result.compatible


def test_tier2_gate_passes_with_path(tmp_path):
    golden = GoldenProbe(
        endpoint_name="checkout",
        endpoint_kind="QUERY",
        category="checkout",
        input_sent='query { checkout(id: "x") { id } }',
        golden_response={
            "errors": [
                {
                    "message": "Invalid ID: x. Expected: Checkout.",
                    "path": ["checkout"],
                }
            ],
            "data": {"checkout": None},
        },
        golden_outcome="not_found_probe",
        golden_status="warn",
        golden_contract="not_found",
        semantic_profile={
            "tier2": {"requires_path": True, "expected_path": ["checkout"]},
        },
    )
    actual = {
        "data": {"checkout": None},
        "errors": [{"message": "Invalid ID: x. Expected: Checkout.", "path": ["checkout"]}],
    }
    result = compare_probe_to_actual(golden, actual, tier2_required=True)
    assert result.compatible
    assert result.match_status == "match"
