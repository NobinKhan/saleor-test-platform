"""Client bundle storage tests."""

import json
from pathlib import Path

import pytest

from app.services.client_bundles import (
    ClientBundle,
    build_client_bundle_endpoints,
    document_hash,
    is_stub_bundle,
    write_bundle,
)
from app.services.client_bundle_schema_gate import compute_client_bundle_schema_gate
from app.services.dashboard_bundle_import import parse_graphql_file


@pytest.fixture
def sample_bundle_dir(tmp_path, monkeypatch):
    import app.services.client_bundles as cb

    root = tmp_path / "client-bundles"
    monkeypatch.setattr(cb, "BUNDLES_ROOT", root)
    gql = tmp_path / "shop.graphql"
    gql.write_text("query ShopDetails { shop { version } }", encoding="utf-8")
    bundles = parse_graphql_file(gql, "shop.graphql")
    for b in bundles:
        write_bundle("dashboard", "3.23.6", b)
    return root


def test_document_hash_stable():
    doc = "query ShopDetails { shop { version } }"
    assert document_hash(doc) == document_hash(doc)


def test_is_stub_bundle_rejects_seed():
    bundle = ClientBundle(
        bundle_id="x",
        source="saleor-dashboard",
        source_path="seed/x.graphql",
        operation_names=["X"],
        document="query X { shop { version } }",
        variables={},
        document_hash="sha256:seed-abc",
    )
    assert is_stub_bundle(bundle) is True


def test_build_endpoints_from_temp_dir(sample_bundle_dir):
    endpoints = build_client_bundle_endpoints("3.23.6", recorded_only=False)
    assert len(endpoints) >= 1


def test_to_golden_probe():
    bundle = ClientBundle(
        bundle_id="test",
        source="saleor-dashboard",
        source_path="x.graphql",
        operation_names=["Test"],
        document="query Test { shop { version } }",
        variables={},
        golden_response={"data": {"shop": {"version": "3.23.7"}}},
        golden_outcome="success_with_data",
        golden_status="pass",
        golden_contract="success",
    )
    probe = bundle.to_golden_probe()
    assert probe.endpoint_kind == "CLIENT_BUNDLE"
    assert probe.endpoint_name == "test"


def test_l3_schema_gate_pass():
    bundle = ClientBundle(
        bundle_id="shop",
        source="saleor-dashboard",
        source_path="q.graphql",
        operation_names=["ShopDetails"],
        document="query ShopDetails { shop { version } }",
        variables={},
        golden_response={"data": {"shop": {"version": "3"}}},
    )
    intro = {"queries": ["shop"], "mutations": []}
    gate = compute_client_bundle_schema_gate([bundle], intro)
    assert gate["client_schema_gate_pass"] is True


def test_l3_schema_gate_fail_missing_field():
    bundle = ClientBundle(
        bundle_id="gone",
        source="saleor-dashboard",
        source_path="q.graphql",
        operation_names=["Gone"],
        document="query Gone { removedField { id } }",
        variables={},
        golden_response={"data": {}},
    )
    intro = {"queries": ["shop"], "mutations": []}
    gate = compute_client_bundle_schema_gate([bundle], intro)
    assert gate["client_schema_gate_pass"] is False
