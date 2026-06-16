"""Tests for auth visibility heuristics."""

from app.services.auth_visibility import infer_is_public, requires_staff_auth


def test_public_checkout_mutations():
    assert infer_is_public("checkoutCreate", "MUTATION") is True
    assert requires_staff_auth({"name": "checkoutCreate", "kind": "MUTATION"}) is False


def test_staff_order_query():
    assert infer_is_public("orders", "QUERY") is False
    assert requires_staff_auth({"name": "orders", "kind": "QUERY"}) is True
