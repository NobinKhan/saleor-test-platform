"""
Auth visibility heuristics for GraphQL operations (replaces legacy L2 static catalog).
"""

from __future__ import annotations

# Storefront / anonymous mutations (no staff JWT required for capture ordering).
PUBLIC_MUTATIONS: frozenset[str] = frozenset({
    "accountRegister",
    "confirmAccount",
    "requestPasswordReset",
    "resetPassword",
    "checkoutCreate",
    "checkoutComplete",
    "checkoutAddPromoCode",
    "checkoutRemovePromoCode",
    "checkoutEmailUpdate",
    "checkoutShippingAddressUpdate",
    "checkoutPaymentCreate",
    "checkoutBillingAddressUpdate",
    "checkoutShippingMethodUpdate",
    "checkoutDeliveryMethodUpdate",
    "checkoutLinesAdd",
    "checkoutLinesUpdate",
    "checkoutLinesDelete",
    "checkoutCustomerAttach",
})

# Staff-only queries (public storefront queries are everything else).
STAFF_ONLY_QUERIES: frozenset[str] = frozenset({
    "me",
    "user",
    "users",
    "orders",
    "order",
    "ordersDraft",
    "ordersByUser",
    "permissionGroups",
    "permissionGroup",
    "giftCards",
    "giftCard",
    "payments",
    "payment",
    "warehouses",
    "warehouse",
    "plugins",
    "plugin",
    "stocks",
    "stock",
    "apps",
    "app",
    "webhooks",
    "webhook",
})


def infer_is_public(name: str, kind: str) -> bool:
    """True when operation is typically callable without staff dashboard JWT."""
    if kind == "MUTATION":
        return name in PUBLIC_MUTATIONS
    if kind == "QUERY":
        return name not in STAFF_ONLY_QUERIES
    return False


def requires_staff_auth(endpoint: dict) -> bool:
    """True when auth_error under staff token indicates a capture defect."""
    if endpoint.get("name") in PUBLIC_MUTATIONS:
        return False
    if endpoint.get("kind") == "MUTATION":
        return True
    return not infer_is_public(endpoint["name"], endpoint["kind"])
