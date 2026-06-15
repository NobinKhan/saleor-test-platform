"""Mocked GraphQL tests for saleor_demo seed mutation helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.demo_seed import (
    DEMO_CHANNEL_USD_SLUG,
    assign_demo_channel_warehouses,
    assign_demo_catalog_products,
    seed_demo_categories,
    seed_demo_collections,
    seed_demo_site_settings,
    seed_demo_shipping_zones,
)


@pytest.mark.asyncio
async def test_seed_demo_site_settings_skips_when_already_true():
    gql = AsyncMock(
        return_value={"shop": {"useLegacyShippingZoneStockAvailability": True}}
    )
    with patch("app.services.demo_seed._gql", gql):
        seeded = await seed_demo_site_settings(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            error_log=[],
        )
    assert seeded == set()
    gql.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_demo_site_settings_updates_when_false():
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
    with patch("app.services.demo_seed._gql", gql):
        seeded = await seed_demo_site_settings(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            error_log=[],
        )
    assert seeded == {"site_settings:legacy_shipping"}
    assert gql.await_count == 2
    mutation_call = gql.await_args_list[1]
    assert mutation_call.kwargs["variables"] == {
        "input": {"useLegacyShippingZoneStockAvailability": True}
    }


@pytest.mark.asyncio
async def test_assign_demo_channel_warehouses_calls_channel_update():
    async def fake_gql(client, *, url, headers, query, variables=None, **kwargs):
        if "channels {" in query and "channelUpdate" not in query:
            return {"channels": [{"id": "CH1", "slug": DEMO_CHANNEL_USD_SLUG}]}
        if "warehouses(first" in query:
            return {
                "warehouses": {
                    "edges": [
                        {"node": {"id": "WH1", "name": "Default Warehouse"}},
                        {"node": {"id": "WH2", "name": "Default"}},
                    ]
                }
            }
        if "channelUpdate" in query:
            return {"channelUpdate": {"channel": {"id": "CH1", "slug": DEMO_CHANNEL_USD_SLUG}}}
        return {}

    with patch("app.services.demo_seed._gql", side_effect=fake_gql):
        seeded = await assign_demo_channel_warehouses(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            fixtures={},
            error_log=[],
        )
    assert f"channel_warehouses:{DEMO_CHANNEL_USD_SLUG}" in seeded


@pytest.mark.asyncio
async def test_seed_demo_shipping_zones_creates_named_zone():
    calls: list[str] = []

    async def fake_gql(client, *, url, headers, query, variables=None, **kwargs):
        if "shippingZones(first" in query:
            return {"shippingZones": {"edges": []}}
        if "channels {" in query:
            return {"channels": [{"id": "CH-USD", "slug": DEMO_CHANNEL_USD_SLUG}]}
        if "warehouses(first" in query:
            return {
                "warehouses": {
                    "edges": [{"node": {"id": "WH1", "name": "Default Warehouse"}}]
                }
            }
        if "shippingZoneCreate" in query:
            calls.append(variables["input"]["name"])
            return {
                "shippingZoneCreate": {
                    "shippingZone": {"id": f"SZ-{variables['input']['name']}", "name": variables["input"]["name"]},
                    "errors": [],
                }
            }
        if "channelUpdate" in query and variables and "addShippingZones" in (variables.get("input") or {}):
            return {"channelUpdate": {"channel": {"id": "CH-PLN"}}}
        return {}

    with patch("app.services.demo_seed._gql", side_effect=fake_gql):
        with patch("app.services.demo_seed._channel_by_slug", new_callable=AsyncMock) as mock_ch:
            mock_ch.side_effect = [
                {"id": "CH-USD", "slug": DEMO_CHANNEL_USD_SLUG},
                {"id": "CH-PLN", "slug": "channel-pln"},
            ]
            seeded = await seed_demo_shipping_zones(
                httpx.AsyncClient(),
                url="http://example.com/graphql/",
                headers={},
                fixtures={},
                error_log=[],
            )
    assert "shipping_zone:Default" in seeded
    assert "Default" in calls


@pytest.mark.asyncio
async def test_seed_demo_categories_creates_root_category():
    calls: list[dict[str, Any]] = []

    async def fake_gql(client, *, url, headers, query, variables=None, **kwargs):
        if "category(slug:" in query:
            return {"category": None}
        if "categoryCreate" in query:
            calls.append(variables["input"])
            return {
                "categoryCreate": {
                    "category": {"id": f"CAT-{variables['input']['slug']}", "slug": variables["input"]["slug"]},
                    "errors": [],
                }
            }
        return {}

    fixtures: dict[str, Any] = {}
    with patch("app.services.demo_seed._gql", side_effect=fake_gql):
        seeded = await seed_demo_categories(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            fixtures=fixtures,
            error_log=[],
        )
    assert "category:default-category" in seeded
    assert fixtures.get("default_category_id") == "CAT-default-category"
    assert any(c["slug"] == "accessories" for c in calls)


@pytest.mark.asyncio
async def test_seed_demo_collections_publishes_on_channel():
    listing_calls: list[list[str]] = []

    async def fake_gql(client, *, url, headers, query, variables=None, **kwargs):
        if "collection(slug:" in query:
            return {"collection": None}
        if "collectionCreate" in query:
            return {
                "collectionCreate": {
                    "collection": {"id": "COL1", "slug": "featured-products"},
                    "errors": [],
                }
            }
        if "collectionChannelListingUpdate" in query:
            channel_ids = [
                ch["channelId"]
                for ch in (variables or {}).get("input", {}).get("addChannels", [])
            ]
            listing_calls.append(channel_ids)
            return {"collectionChannelListingUpdate": {"errors": []}}
        return {}

    fixtures = {
        "default_channel": DEMO_CHANNEL_USD_SLUG,
        "default_channel_id": "CH-USD",
        "storefront_channel": "channel-pln",
        "storefront_channel_id": "CH-PLN",
    }
    with patch("app.services.demo_seed._gql", side_effect=fake_gql):
        seeded = await seed_demo_collections(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            fixtures=fixtures,
            error_log=[],
        )
    assert "collection:featured-products" in seeded
    assert fixtures["default_collection_id"] == "COL1"
    assert listing_calls == [["CH-USD", "CH-PLN"]]


@pytest.mark.asyncio
async def test_assign_demo_catalog_products_links_product():
    async def fake_gql(client, *, url, headers, query, variables=None, **kwargs):
        if "category(slug:" in query:
            return {"category": {"id": "CAT-JUICES", "slug": "juices"}}
        if "productUpdate" in query:
            return {"productUpdate": {"product": {"id": "PROD1"}, "errors": []}}
        if "collectionAddProducts" in query:
            return {"collectionAddProducts": {"collection": {"id": "COL1"}, "errors": []}}
        return {}

    fixtures = {"default_product_id": "PROD1", "default_collection_id": "COL1"}
    with patch("app.services.demo_seed._gql", side_effect=fake_gql):
        seeded = await assign_demo_catalog_products(
            httpx.AsyncClient(),
            url="http://example.com/graphql/",
            headers={},
            fixtures=fixtures,
            error_log=[],
        )
    assert "product_category:juices" in seeded
    assert "collection_product:apple-juice" in seeded
