"""Tests for input variant matrix."""

from app.services.variant_corpus import build_variant_endpoints, load_variant_matrix


def test_product_create_variants_loaded():
    variants = load_variant_matrix("productCreate")
    assert len(variants) >= 3
    tags = {t for v in variants for t in v.tags}
    assert "invalid" in tags


def test_build_variant_endpoints():
    endpoints = build_variant_endpoints(operation_names=["productCreate"], recorded_only=False)
    assert len(endpoints) >= 3
    assert all(e["kind"] == "VARIANT_PROBE" for e in endpoints)
