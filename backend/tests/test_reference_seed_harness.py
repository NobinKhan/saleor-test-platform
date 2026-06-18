"""Harness topology seed helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.reference_seed import (
    REFERENCE_PRODUCT_SLUG,
    _ensure_reference_product,
    _ensure_shop_settings,
)


@pytest.mark.asyncio
async def test_ensure_shop_settings_skips_when_already_enabled():
    gql = AsyncMock(
        return_value={"shop": {"useLegacyShippingZoneStockAvailability": True}}
    )
    with patch("app.services.reference_seed._gql", gql):
        seeded = await _ensure_shop_settings(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            error_log=[],
        )
    assert seeded == set()
    gql.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_shop_settings_updates_when_disabled():
    gql = AsyncMock(
        side_effect=[
            {"shop": {"useLegacyShippingZoneStockAvailability": False}},
            {
                "shopSettingsUpdate": {
                    "shop": {"useLegacyShippingZoneStockAvailability": True},
                    "errors": [],
                }
            },
        ]
    )
    with patch("app.services.reference_seed._gql", gql):
        seeded = await _ensure_shop_settings(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            error_log=[],
        )
    assert seeded == {"site_settings:legacy_shipping"}
    assert gql.await_count == 2


@pytest.mark.asyncio
async def test_ensure_reference_product_creates_variant_when_product_has_none():
    fixtures = {
        "default_channel_id": "Q2hhbm5lbDox",
        "default_channel": "harness-channel",
        "default_product_type_id": "UHJvZHVjdFR5cGU6MQ==",
    }
    gql = AsyncMock(
        side_effect=[
            {
                "product": {
                    "id": "UHJvZHVjdDox",
                    "slug": REFERENCE_PRODUCT_SLUG,
                    "variants": [],
                    "channelListings": [{"channel": {"id": "Q2hhbm5lbDox"}}],
                }
            },
            {
                "productVariantCreate": {
                    "productVariant": {"id": "UHJvZHVjdFZhcmlhbnQ6MQ=="},
                    "errors": [],
                }
            },
        ]
    )
    with patch("app.services.reference_seed._gql", gql):
        created = await _ensure_reference_product(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            fixtures=fixtures,
            error_log=[],
        )
    assert created is True
    assert fixtures["default_variant_id"] == "UHJvZHVjdFZhcmlhbnQ6MQ=="
    assert fixtures["variant_id_for_cart"] == "UHJvZHVjdFZhcmlhbnQ6MQ=="


@pytest.mark.asyncio
async def test_certification_topology_preserves_seeded_entities_after_capture():
    from app.services.reference_seed import SeedResult, ensure_certification_topology

    runtime = SeedResult(
        fixtures={
            "default_order_id": "T3JkZXI6MQ==",
            "default_channel": "harness-channel",
            "default_channel_id": "Q2hhbm5lbDox",
        },
        seeded_keys=frozenset({"default_order_id", "default_channel", "default_channel_id"}),
    )
    captured = {
        "default_channel": "default-channel",
        "default_variant_id": "UHJvZHVjdFZhcmlhbnQ6MQ==",
    }

    async def _passthrough_storefront(*_args, fixtures, **_kwargs):
        return fixtures

    with (
        patch(
            "app.services.reference_seed.ensure_runtime_fixture_entities",
            AsyncMock(return_value=runtime),
        ),
        patch(
            "app.services.reference_seed._ensure_catalog_categories",
            AsyncMock(return_value=set()),
        ),
        patch(
            "app.services.reference_seed._capture_fixtures",
            AsyncMock(return_value=captured),
        ),
        patch(
            "app.services.reference_seed._seed_storefront_fixtures",
            AsyncMock(side_effect=_passthrough_storefront),
        ),
        patch(
            "app.services.reference_seed._ensure_dummy_payment_gateway",
            AsyncMock(return_value=set()),
        ),
        patch(
            "app.services.reference_seed._ensure_shop_settings",
            AsyncMock(return_value=set()),
        ),
    ):
        result = await ensure_certification_topology("http://example.com/graphql/", "token")

    assert result.fixtures["default_order_id"] == "T3JkZXI6MQ=="
    assert result.fixtures["default_channel"] == "harness-channel"
