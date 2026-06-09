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
