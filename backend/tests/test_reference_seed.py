"""Tests for reference seed fixture keys."""

import pytest

from app.services.client_bundle_fixtures import substitute_fixtures


def test_substitute_all_reference_fixture_keys():
    variables = {
        "channelId": "{{fixtures.default_channel_id}}",
        "productId": "{{fixtures.default_product_id}}",
        "variantId": "{{fixtures.default_variant_id}}",
        "orderId": "{{fixtures.default_order_id}}",
        "customerId": "{{fixtures.default_customer_id}}",
        "collectionId": "{{fixtures.default_collection_id}}",
    }
    fixtures = {
        "default_channel_id": "ch-1",
        "default_product_id": "prod-1",
        "default_variant_id": "var-1",
        "default_order_id": "ord-1",
        "default_customer_id": "cust-1",
        "default_collection_id": "coll-1",
    }
    result = substitute_fixtures(variables, fixtures)
    assert result["channelId"] == "ch-1"
    assert result["orderId"] == "ord-1"


def test_substitute_missing_fixture_raises_keyerror():
    with pytest.raises(KeyError, match="default_order_id"):
        substitute_fixtures({"id": "{{fixtures.default_order_id}}"}, {})
