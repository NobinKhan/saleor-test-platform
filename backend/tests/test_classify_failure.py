"""Unit tests for failure category classification (seed prerequisites)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.test_runner import _classify_failure_category


def _comparison(*, compatible=False, match_status="shape_drift", **kwargs):
    defaults = {
        "compatible": compatible,
        "match_status": match_status,
        "actual_contract": "success_with_data",
        "diff_summary": "field path drift",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_compatible_returns_compatible():
    cat = _classify_failure_category(
        comparison=_comparison(compatible=True),
        kind="CLIENT_BUNDLE",
        endpoint_name="channels",
        meta={},
        assertion_failures=[],
    )
    assert cat == "compatible"


def test_sitesettings_shape_drift_is_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="sitesettings",
        meta={},
        assertion_failures=[],
        endpoint={"seed_tags": ["requires_catalog_seed"]},
    )
    assert cat == "seed_prerequisite"


def test_seed_tagged_shape_drift_is_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="channeldiagnostics",
        meta={},
        assertion_failures=[],
        endpoint={"seed_tags": ["requires_catalog_seed"]},
    )
    assert cat == "seed_prerequisite"


def test_seed_tagged_shape_drift_with_order_fixture_tag():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="orderfulfilldata",
        meta={},
        assertion_failures=[],
        endpoint={"seed_tags": ["requires_order_fixture"]},
    )
    assert cat == "seed_prerequisite"


def test_untagged_shape_drift_is_data_drift():
    """Untagged CLIENT_BUNDLE shape_drift with generic diff is data drift (not real bug)."""
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="productdetails",
        meta={},
        assertion_failures=[],
    )
    assert cat == "data_drift"


def test_shape_drift_with_type_mismatch_is_schema_mismatch():
    cat = _classify_failure_category(
        comparison=_comparison(
            match_status="shape_drift",
            diff_summary="Normalized shape differs: type_mismatch at $.data.product.name",
        ),
        kind="CLIENT_BUNDLE",
        endpoint_name="productdetails",
        meta={},
        assertion_failures=[],
    )
    assert cat == "schema_mismatch"


def test_seed_tagged_mismatch_is_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="mismatch", actual_contract="business_error"),
        kind="CLIENT_BUNDLE",
        endpoint_name="productvariantsetdefault",
        meta={},
        assertion_failures=[],
        endpoint={"seed_tags": ["requires_demo_product_variant"]},
    )
    assert cat == "seed_prerequisite"


def test_scenario_not_found_is_data_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(
            match_status="mismatch",
            actual_contract="not_found",
            diff_summary="Product not found",
        ),
        kind="SCENARIO_STEP",
        endpoint_name="product-lifecycle/06_list_after_delete",
        meta={},
        assertion_failures=[],
    )
    assert cat == "data_prerequisite"


def test_checkout_access_denied_is_data_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(
            match_status="mismatch",
            actual_contract="graphql_error",
            diff_summary="Checkout access denied for anonymous user",
        ),
        kind="CLIENT_BUNDLE",
        endpoint_name="sf-checkoutlinesadd",
        meta={},
        assertion_failures=[],
    )
    assert cat == "data_prerequisite"


def test_empty_catalog_edges_is_data_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(
            match_status="shape_drift",
            diff_summary='search.edges: [] vs golden 10 edges',
        ),
        kind="CLIENT_BUNDLE",
        endpoint_name="somecatalogprobe",
        meta={},
        assertion_failures=[],
    )
    assert cat == "data_prerequisite"


def test_searchcategories_seed_tagged_stays_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(
            match_status="shape_drift",
            diff_summary='search.edges: [] vs golden 10 edges',
        ),
        kind="CLIENT_BUNDLE",
        endpoint_name="searchcategories",
        meta={},
        assertion_failures=[],
        endpoint={"seed_tags": ["requires_catalog_seed"]},
    )
    assert cat == "seed_prerequisite"
