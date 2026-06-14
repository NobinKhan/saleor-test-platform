"""Probe tier classification tests."""

from app.services.probe_tiers import (
    classify_probe_tier,
    tier_label,
    tier_concurrency,
)


def _endpoint(kind="QUERY", category="products", name="products"):
    return {"kind": kind, "category": category, "name": name}


def test_query_tier_0():
    assert classify_probe_tier(_endpoint(kind="QUERY")) == 0


def test_mutation_in_tier_0_category():
    assert classify_probe_tier(_endpoint(kind="MUTATION", category="products")) == 0


def test_mutation_outside_tier_0():
    assert classify_probe_tier(_endpoint(kind="MUTATION", category="orders")) == 1


def test_client_bundle_query_tier_0():
    ep = {
        "kind": "CLIENT_BUNDLE",
        "bundle_document": "query ProductList { products(first: 1) { edges { node { id } } } }",
    }
    assert classify_probe_tier(ep) == 0


def test_client_bundle_mutation_tier_1():
    ep = {
        "kind": "CLIENT_BUNDLE",
        "bundle_document": "mutation ProductCreate($input: ProductCreateInput!) { productCreate(input: $input) { product { id } } }",
    }
    assert classify_probe_tier(ep) == 1


def test_scenario_tier_2():
    assert classify_probe_tier(_endpoint(kind="SCENARIO_KIND")) == 2
    assert classify_probe_tier(_endpoint(kind="SCENARIO_STEP")) == 2


def test_dynamic_probe_tier_3():
    assert classify_probe_tier(_endpoint(kind="DYNAMIC_PROBE")) == 3


def test_variant_probe_tier_1():
    assert classify_probe_tier(_endpoint(kind="VARIANT_PROBE")) == 1


def test_unknown_kind_defaults_to_1():
    assert classify_probe_tier(_endpoint(kind="UNKNOWN")) == 1


def test_tier_label_0():
    assert tier_label(0) == "parallel-read"


def test_tier_label_1():
    assert tier_label(1) == "sequential-mutate"


def test_tier_label_2():
    assert tier_label(2) == "scenario-ordered"


def test_tier_label_3():
    assert tier_label(3) == "dynamic-sequential"


def test_tier_label_unknown():
    assert tier_label(99) == "tier-99"


def test_tier_concurrency_0():
    c = tier_concurrency(0)
    assert c >= 1
    assert c <= 10


def test_tier_concurrency_sequential():
    assert tier_concurrency(1) == 1
    assert tier_concurrency(2) == 1
    assert tier_concurrency(3) == 1
