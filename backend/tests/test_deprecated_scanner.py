"""Deprecated scanner tests."""

from app.services.deprecated_scanner import (
    scan_document_for_deprecated_types,
    is_deprecated_bundle,
    filter_deprecated_bundles,
    scan_l1_probe_for_deprecated,
    get_deprecated_types,
)

from app.services.client_bundles import ClientBundle


def test_get_deprecated_types_sorted():
    types = get_deprecated_types()
    assert types == sorted(types)
    assert "Sale" in types
    assert "VoucherDiscountType" in types


def test_scan_document_finds_sale():
    doc = "type Sale { id }"
    found = scan_document_for_deprecated_types(doc)
    assert "Sale" in found


def test_scan_document_clean():
    doc = "mutation { productCreate }"
    found = scan_document_for_deprecated_types(doc)
    assert found == []


def test_scan_document_multiple():
    doc = "type Sale { id } type SaleChannelListing { channel } type VoucherDiscountType { value }"
    found = scan_document_for_deprecated_types(doc)
    assert "Sale" in found
    assert "SaleChannelListing" in found
    assert "VoucherDiscountType" in found


def test_is_deprecated_bundle_clean():
    bundle = ClientBundle(
        bundle_id="test_clean",
        source="dashboard",
        source_path="bundles/clean.graphql.json",
        operation_names=["products"],
        document="query { products }",
        variables={},
    )
    is_dep, types_found = is_deprecated_bundle(bundle)
    assert not is_dep
    assert types_found == []


def test_is_deprecated_bundle_dirty():
    bundle = ClientBundle(
        bundle_id="test_sale",
        source="dashboard",
        source_path="bundles/sale.graphql.json",
        operation_names=["sale"],
        document="query { Sale(id: 1) { id } }",
        variables={},
    )
    is_dep, types_found = is_deprecated_bundle(bundle)
    assert is_dep
    assert "Sale" in types_found


def test_filter_deprecated_bundles():
    clean = ClientBundle(
        bundle_id="clean", source="dashboard",
        source_path="bundles/clean.graphql.json",
        operation_names=["products"],
        document="query { products }", variables={},
    )
    dirty = ClientBundle(
        bundle_id="dirty", source="dashboard",
        source_path="bundles/dirty.graphql.json",
        operation_names=["Sale"],
        document="query { Sale { id } }", variables={},
    )
    compatible, excluded = filter_deprecated_bundles([clean, dirty])
    assert len(compatible) == 1
    assert compatible[0].bundle_id == "clean"
    assert len(excluded) == 1
    assert excluded[0]["bundle_id"] == "dirty"
    assert excluded[0]["reason"] == "deprecated_type"
    assert "Sale" in excluded[0]["deprecated_types"]


def test_scan_l1_probe_clean():
    is_dep, types_found = scan_l1_probe_for_deprecated("mutation { productCreate }")
    assert not is_dep
    assert types_found == []


def test_scan_l1_probe_dirty():
    is_dep, types_found = scan_l1_probe_for_deprecated("type SaleTranslatableContent { id }")
    assert is_dep
    assert "SaleTranslatableContent" in types_found
