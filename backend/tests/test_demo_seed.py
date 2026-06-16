"""Unit tests for saleor_demo seed topology constants and helpers."""

from app.services.demo_seed import (
    DEMO_CHANNEL_PLN_SLUG,
    DEMO_CHANNEL_USD_SLUG,
    DEMO_CUSTOMERS,
    DEMO_SHIPPING_ZONE_SPECS,
    DEMO_WAREHOUSE_NAMES,
)
from app.services.seed_tags import SEED_TAGGED_BUNDLES


def test_demo_customers_match_searchcustomersoperands_golden_emails():
    emails = {email for email, _, _ in DEMO_CUSTOMERS}
    assert "jade.guerrero@example.com" in emails
    assert "harness-reference-customer@example.com" not in emails
    assert len(DEMO_CUSTOMERS) == 10


def test_storefront_customer_has_empty_names():
    storefront = next(
        row for row in DEMO_CUSTOMERS if row[0] == "harness-storefront-customer@example.com"
    )
    assert storefront[1] == ""
    assert storefront[2] == ""


def test_demo_warehouse_includes_click_and_collect():
    assert "Default for click and collect" in DEMO_WAREHOUSE_NAMES
    assert len(DEMO_WAREHOUSE_NAMES) == 8


def test_demo_shipping_zone_specs_cover_channeldiagnostics_names():
    names = {spec[0] for spec in DEMO_SHIPPING_ZONE_SPECS}
    assert names == {"Default", "Europe", "Oceania", "Asia", "Americas", "Africa"}


def test_demo_channels_are_two_channel_golden_slugs():
    assert DEMO_CHANNEL_USD_SLUG == "default-channel"
    assert DEMO_CHANNEL_PLN_SLUG == "channel-pln"


def test_seed_tag_registry_cleared_for_mutation_first():
    """Static seed tag registry retired — tags live on bundle JSON when needed."""
    assert SEED_TAGGED_BUNDLES == {}
