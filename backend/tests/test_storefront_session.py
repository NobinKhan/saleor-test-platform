"""Tests for storefront customer + checkout session preamble."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.services.storefront_session import ensure_storefront_session


@pytest.mark.asyncio
async def test_ensure_storefront_session_updates_profile_and_checkout():
    gql = AsyncMock(
        side_effect=[
            {
                "accountUpdate": {
                    "user": {"id": "U1", "firstName": "Harness", "lastName": "Updated"},
                    "errors": [],
                }
            },
            {
                "checkoutCreate": {
                    "checkout": {"id": "CHK1", "token": "tok-1"},
                    "errors": [],
                }
            },
            {"checkoutLinesAdd": {"checkout": {"id": "CHK1"}, "errors": []}},
            {"checkoutShippingAddressUpdate": {"checkout": {"id": "CHK1"}, "errors": []}},
            {"checkout": {"availableShippingMethods": [{"id": "SHIP1", "name": "Default"}]}},
            {
                "checkoutCustomerAttach": {
                    "checkout": {"id": "CHK1", "user": {"id": "U1"}},
                    "errors": [],
                }
            },
        ]
    )
    fixtures: dict[str, Any] = {
        "storefront_channel": "harness-channel",
        "variant_id_for_cart": "VAR1",
        "storefront_customer_id": "U1",
    }
    with patch("app.services.storefront_session._gql", gql):
        updated, seeded, errors = await ensure_storefront_session(
            "http://example.com/graphql/",
            customer_token="cust-jwt",
            fixtures=fixtures,
            timeout=5,
        )
    assert errors == []
    assert "storefront_customer_profile" in seeded
    assert "storefront_checkout_session" in seeded
    assert "storefront_checkout_customer_attach" in seeded
    assert updated["default_checkout_id"] == "CHK1"
    assert updated["default_checkout_token"] == "tok-1"
    assert updated["delivery_method_id"] == "SHIP1"
    create_call = gql.await_args_list[1]
    assert create_call.kwargs["variables"]["input"]["channel"] == "harness-channel"


@pytest.mark.asyncio
async def test_ensure_storefront_session_reuses_existing_checkout():
    gql = AsyncMock(
        side_effect=[
            {
                "accountUpdate": {
                    "user": {"id": "U1", "firstName": "Harness", "lastName": "Updated"},
                    "errors": [],
                }
            },
            {"checkout": {"availableShippingMethods": [{"id": "SHIP1", "name": "UPS"}]}},
        ]
    )
    fixtures = {"default_checkout_id": "CHK-EXISTING", "storefront_customer_id": "U1"}
    with patch("app.services.storefront_session._gql", gql):
        updated, seeded, _ = await ensure_storefront_session(
            "http://example.com/graphql/",
            customer_token="cust-jwt",
            fixtures=fixtures,
            timeout=5,
        )
    assert updated["default_checkout_id"] == "CHK-EXISTING"
    assert "storefront_checkout_session" in seeded
    assert "storefront_checkout_customer_attach" not in seeded
    assert gql.await_count == 2


@pytest.mark.asyncio
async def test_ensure_storefront_session_skips_profile_without_token():
    gql = AsyncMock(
        side_effect=[
            {
                "checkoutCreate": {
                    "checkout": {"id": "CHK1", "token": "tok-1"},
                    "errors": [],
                }
            },
            {"checkoutLinesAdd": {"checkout": {"id": "CHK1"}, "errors": []}},
            {"checkoutShippingAddressUpdate": {"checkout": {"id": "CHK1"}, "errors": []}},
            {"checkout": {"availableShippingMethods": []}},
        ]
    )
    fixtures = {"default_channel": "harness-channel", "default_variant_id": "VAR1"}
    with patch("app.services.storefront_session._gql", gql):
        updated, seeded, _ = await ensure_storefront_session(
            "http://example.com/graphql/",
            customer_token=None,
            fixtures=fixtures,
            timeout=5,
        )
    assert "storefront_customer_profile" not in seeded
    assert "storefront_checkout_customer_attach" not in seeded
    assert updated["default_checkout_id"] == "CHK1"
