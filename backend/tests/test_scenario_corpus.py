"""Tests for L4 scenario corpus."""

from app.services.scenario_corpus import (
    build_scenario_endpoints,
    load_all_scenarios,
    substitute_scenario_variables,
)


def test_product_lifecycle_manifest_loaded():
    manifests = load_all_scenarios()
    ids = {m.scenario_id for m in manifests}
    assert "product-lifecycle" in ids
    assert "checkout-lifecycle" in ids
    assert "order-lifecycle" in ids


def test_build_checkout_lifecycle_endpoints():
    endpoints = build_scenario_endpoints(scenario_ids=["checkout-lifecycle"])
    assert len(endpoints) == 6
    assert endpoints[3]["auth_context"] == "customer"


def test_build_order_lifecycle_endpoints():
    endpoints = build_scenario_endpoints(scenario_ids=["order-lifecycle"])
    assert len(endpoints) == 3
    assert all(ep["auth_context"] == "staff" for ep in endpoints)


def test_build_scenario_endpoints():
    endpoints = build_scenario_endpoints(scenario_ids=["product-lifecycle"])
    assert len(endpoints) == 6
    assert endpoints[0]["kind"] == "SCENARIO_STEP"


def test_substitute_scenario_variables():
    result = substitute_scenario_variables(
        {"id": "{{context.created_product_id}}", "slug": "{{fixtures.default_slug}}"},
        {"created_product_id": "abc"},
        {"default_slug": "test-slug"},
    )
    assert result["id"] == "abc"
    assert result["slug"] == "test-slug"
