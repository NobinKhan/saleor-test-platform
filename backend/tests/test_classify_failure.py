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


def test_seed_tagged_shape_drift_is_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="channeldiagnostics",
        meta={},
        assertion_failures=[],
        demo_seed_profile="harness",
    )
    assert cat == "seed_prerequisite"


def test_seed_tagged_shape_drift_after_saleor_demo_still_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="orderfulfilldata",
        meta={},
        assertion_failures=[],
        demo_seed_profile="saleor_demo",
    )
    assert cat == "seed_prerequisite"


def test_untagged_shape_drift_is_real_bug():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="shape_drift"),
        kind="CLIENT_BUNDLE",
        endpoint_name="productdetails",
        meta={},
        assertion_failures=[],
        demo_seed_profile="harness",
    )
    assert cat == "real_bug"


def test_seed_tagged_mismatch_harness_profile_is_seed_prerequisite():
    cat = _classify_failure_category(
        comparison=_comparison(match_status="mismatch", actual_contract="business_error"),
        kind="CLIENT_BUNDLE",
        endpoint_name="productvariantsetdefault",
        meta={},
        assertion_failures=[],
        demo_seed_profile="harness",
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
