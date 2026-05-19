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
