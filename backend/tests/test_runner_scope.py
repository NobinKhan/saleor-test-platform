"""Tests for endpoint list building."""

from app.services.test_runner import (
    SALEOR_MUTATIONS,
    SALEOR_QUERIES,
    build_endpoints_list,
)


def test_full_scope_includes_queries_and_mutations():
    endpoints = build_endpoints_list("full", public_only=False)
    names = {e["name"] for e in endpoints}
    assert "products" in names
    assert "productCreate" in names
    assert len(endpoints) == len(SALEOR_QUERIES) + len(SALEOR_MUTATIONS)


def test_catalog_scope_matches_static_catalog():
    endpoints = build_endpoints_list("catalog", public_only=False)
    assert len(endpoints) == len(SALEOR_QUERIES) + len(SALEOR_MUTATIONS)


def test_queries_scope_only():
    endpoints = build_endpoints_list("queries", public_only=False)
    assert all(e["kind"] == "QUERY" for e in endpoints)
    assert len(endpoints) == len(SALEOR_QUERIES)


def test_mutations_scope_only():
    endpoints = build_endpoints_list("mutations", public_only=False)
    assert all(e["kind"] == "MUTATION" for e in endpoints)


def test_custom_scope_filters_categories():
    endpoints = build_endpoints_list("custom", public_only=False, categories=["shop"])
    assert endpoints
    assert all(e["category"] == "shop" for e in endpoints)


def test_public_only_filter():
    endpoints = build_endpoints_list("full", public_only=True)
    assert all(e["is_public"] for e in endpoints)


def test_client_dashboard_scope_endpoints():
    from app.services.client_bundles import build_client_bundle_endpoints

    endpoints = build_client_bundle_endpoints("3.23.6", recorded_only=False)
    assert len(endpoints) >= 2
    assert all(e["kind"] == "CLIENT_BUNDLE" for e in endpoints)


def test_certification_l3_set_independent_of_extra_target_fields():
    """L3 bundle count must not grow when target schema has extra dashboard fields."""
    from app.core.config import settings
    from app.services.client_bundles import build_client_bundle_endpoints
    from app.services.test_runner import build_golden_endpoints, load_reference_schema

    corpus_ver = settings.golden_corpus_version
    golden_schema = load_reference_schema(corpus_ver)
    inflated_schema = {
        "queries": list(golden_schema["queries"])
        + ["exportProducts", "orderSettings", "authenticated", "authenticating"],
        "mutations": list(golden_schema["mutations"])
        + ["exportGiftCards", "orderSettingsUpdate"],
    }

    l3_golden = build_client_bundle_endpoints(recorded_only=True, schema_intro=golden_schema)
    l3_inflated = build_client_bundle_endpoints(recorded_only=True, schema_intro=inflated_schema)
    # 415 L3 dashboard bundles on disk (11 deprecated Sale API bundles removed from corpus)
    assert len(l3_inflated) == len(l3_golden) == 415

    from app.services.scenario_corpus import build_scenario_endpoints
    from app.services.variant_corpus import build_variant_endpoints
    from app.services.dynamic_corpus import build_dynamic_probe_endpoints

    l1 = build_golden_endpoints(corpus_ver, "full", False, None)
    l3_sf = build_client_bundle_endpoints(
        source="storefront", recorded_only=True, schema_intro=golden_schema
    )
    scenarios = build_scenario_endpoints(recorded_only=False)
    variants = build_variant_endpoints(recorded_only=True)
    dynamic = build_dynamic_probe_endpoints("test-run")
    full_system = len(l1) + len(l3_golden) + len(l3_sf) + len(scenarios) + len(variants) + len(dynamic)
    # 387 L1 + 415 L3 dashboard + 31 L3 storefront + 15 scenarios + 3 variants + 5 dynamic
    assert full_system == 856
