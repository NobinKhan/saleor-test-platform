"""Tests for storefront bundle import."""

from app.services.storefront_bundle_import import scan_storefront_bundles, storefront_vendor_path


def test_storefront_vendor_exists():
    vendor = storefront_vendor_path("3.23.6")
    assert vendor.is_dir(), f"Missing vendor tree: {vendor}"


def test_scan_storefront_bundles_finds_operations():
    vendor = storefront_vendor_path("3.23.6")
    src = vendor / "src"
    bundles = scan_storefront_bundles(src)
    assert len(bundles) >= 5
    names = {b.bundle_id for b in bundles}
    assert any("product" in n for n in names)


def test_storefront_bundles_have_auth_context():
    vendor = storefront_vendor_path("3.23.6")
    bundles = scan_storefront_bundles(vendor / "src")
    contexts = {b.auth_context for b in bundles}
    assert "anonymous" in contexts
