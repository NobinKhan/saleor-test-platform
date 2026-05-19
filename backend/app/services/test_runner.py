"""
app/services/test_runner.py — Core GraphQL testing engine.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx

from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.introspection import (
    compare_schema,
    compare_two_introspections,
    introspect_saleor,
)

# Saleor reference queries/mutations
SALEOR_QUERIES: list[dict] = [
    # Products
    {"name": "products", "kind": "QUERY", "category": "products", "is_public": True},
    {"name": "product", "kind": "QUERY", "category": "products", "is_public": True},
    {"name": "productTypes", "kind": "QUERY", "category": "products", "is_public": True},
    {"name": "productType", "kind": "QUERY", "category": "products", "is_public": True},
    # Orders
    {"name": "orders", "kind": "QUERY", "category": "orders", "is_public": False},
    {"name": "order", "kind": "QUERY", "category": "orders", "is_public": False},
    {"name": "ordersDraft", "kind": "QUERY", "category": "orders", "is_public": False},
    {"name": "ordersByUser", "kind": "QUERY", "category": "orders", "is_public": False},
    # Checkout
    {"name": "checkout", "kind": "QUERY", "category": "checkout", "is_public": True},
    {"name": "checkouts", "kind": "QUERY", "category": "checkout", "is_public": True},
    # Channels
    {"name": "channels", "kind": "QUERY", "category": "channels", "is_public": True},
    {"name": "channel", "kind": "QUERY", "category": "channels", "is_public": True},
    # Categories
    {"name": "categories", "kind": "QUERY", "category": "categories", "is_public": True},
    {"name": "category", "kind": "QUERY", "category": "categories", "is_public": True},
    # Collections
    {"name": "collections", "kind": "QUERY", "category": "collections", "is_public": True},
    {"name": "collection", "kind": "QUERY", "category": "collections", "is_public": True},
    # Attributes
    {"name": "attributes", "kind": "QUERY", "category": "attributes", "is_public": True},
    {"name": "attribute", "kind": "QUERY", "category": "attributes", "is_public": True},
    # Account
    {"name": "me", "kind": "QUERY", "category": "account", "is_public": False},
    {"name": "users", "kind": "QUERY", "category": "account", "is_public": False},
    {"name": "user", "kind": "QUERY", "category": "account", "is_public": False},
    {"name": "permissionGroups", "kind": "QUERY", "category": "account", "is_public": False},
    # Gift cards
    {"name": "giftCards", "kind": "QUERY", "category": "giftcards", "is_public": False},
    {"name": "giftCard", "kind": "QUERY", "category": "giftcards", "is_public": False},
    # Shipping
    {"name": "shippingZones", "kind": "QUERY", "category": "shipping", "is_public": True},
    {"name": "shippingZone", "kind": "QUERY", "category": "shipping", "is_public": True},
    {"name": "shippingMethods", "kind": "QUERY", "category": "shipping", "is_public": True},
    # Payments
    {"name": "payments", "kind": "QUERY", "category": "payments", "is_public": False},
    {"name": "payment", "kind": "QUERY", "category": "payments", "is_public": False},
    # Discounts
    {"name": "sales", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "sale", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "vouchers", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "voucher", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "promotions", "kind": "QUERY", "category": "discounts", "is_public": True},
    # Warehouse
    {"name": "warehouses", "kind": "QUERY", "category": "warehouse", "is_public": False},
    {"name": "warehouse", "kind": "QUERY", "category": "warehouse", "is_public": False},
    # Shop
    {"name": "shop", "kind": "QUERY", "category": "shop", "is_public": True},
    {"name": "paymentGateways", "kind": "QUERY", "category": "shop", "is_public": True},
    {"name": "languages", "kind": "QUERY", "category": "shop", "is_public": True},
    # Pages
    {"name": "pages", "kind": "QUERY", "category": "pages", "is_public": True},
    {"name": "page", "kind": "QUERY", "category": "pages", "is_public": True},
    # Plugins
    {"name": "plugins", "kind": "QUERY", "category": "plugins", "is_public": False},
    {"name": "plugin", "kind": "QUERY", "category": "plugins", "is_public": False},
    # Webhooks
    {"name": "webhookEvents", "kind": "QUERY", "category": "webhooks", "is_public": False},
    # Meta
    {"name": "meta", "kind": "QUERY", "category": "meta", "is_public": True},
]

SALEOR_MUTATIONS: list[dict] = [
    # Products
    {"name": "productCreate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productUpdate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productDelete", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productVariantCreate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productVariantUpdate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productVariantDelete", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productTypeCreate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productTypeUpdate", "kind": "MUTATION", "category": "products", "is_public": False},
    {"name": "productTypeDelete", "kind": "MUTATION", "category": "products", "is_public": False},
    # Orders
    {"name": "orderCreate", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderUpdate", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderDelete", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderConfirm", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderCancel", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderFulfill", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderRefund", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderLineDelete", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderLineUpdate", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderLineAdd", "kind": "MUTATION", "category": "orders", "is_public": False},
    # Checkout
    {"name": "checkoutCreate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutDelete", "kind": "MUTATION", "category": "checkout", "is_public": False},
    {"name": "checkoutComplete", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutAddPromoCode", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutRemovePromoCode", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutEmailUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutShippingAddressUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutShippingMethodUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutPaymentCreate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    # Channels
    {"name": "channelCreate", "kind": "MUTATION", "category": "channels", "is_public": False},
    {"name": "channelUpdate", "kind": "MUTATION", "category": "channels", "is_public": False},
    {"name": "channelDelete", "kind": "MUTATION", "category": "channels", "is_public": False},
    # Categories
    {"name": "categoryCreate", "kind": "MUTATION", "category": "categories", "is_public": False},
    {"name": "categoryUpdate", "kind": "MUTATION", "category": "categories", "is_public": False},
    {"name": "categoryDelete", "kind": "MUTATION", "category": "categories", "is_public": False},
    # Collections
    {"name": "collectionCreate", "kind": "MUTATION", "category": "collections", "is_public": False},
    {"name": "collectionUpdate", "kind": "MUTATION", "category": "collections", "is_public": False},
    {"name": "collectionDelete", "kind": "MUTATION", "category": "collections", "is_public": False},
    {"name": "collectionAddProducts", "kind": "MUTATION", "category": "collections", "is_public": False},
    {"name": "collectionRemoveProducts", "kind": "MUTATION", "category": "collections", "is_public": False},
    # Attributes
    {"name": "attributeCreate", "kind": "MUTATION", "category": "attributes", "is_public": False},
    {"name": "attributeUpdate", "kind": "MUTATION", "category": "attributes", "is_public": False},
    {"name": "attributeDelete", "kind": "MUTATION", "category": "attributes", "is_public": False},
    # Account
    {"name": "accountRegister", "kind": "MUTATION", "category": "account", "is_public": True},
    {"name": "accountUpdate", "kind": "MUTATION", "category": "account", "is_public": False},
    {"name": "accountRequestDeletion", "kind": "MUTATION", "category": "account", "is_public": False},
    {"name": "confirmAccount", "kind": "MUTATION", "category": "account", "is_public": True},
    {"name": "requestPasswordReset", "kind": "MUTATION", "category": "account", "is_public": True},
    {"name": "resetPassword", "kind": "MUTATION", "category": "account", "is_public": True},
    {"name": "passwordChange", "kind": "MUTATION", "category": "account", "is_public": False},
    # Gift cards
    {"name": "giftCardCreate", "kind": "MUTATION", "category": "giftcards", "is_public": False},
    {"name": "giftCardUpdate", "kind": "MUTATION", "category": "giftcards", "is_public": False},
    {"name": "giftCardDelete", "kind": "MUTATION", "category": "giftcards", "is_public": False},
    {"name": "giftCardResend", "kind": "MUTATION", "category": "giftcards", "is_public": False},
    # Shipping
    {"name": "shippingZoneCreate", "kind": "MUTATION", "category": "shipping", "is_public": False},
    {"name": "shippingZoneUpdate", "kind": "MUTATION", "category": "shipping", "is_public": False},
    {"name": "shippingZoneDelete", "kind": "MUTATION", "category": "shipping", "is_public": False},
    {"name": "shippingMethodCreate", "kind": "MUTATION", "category": "shipping", "is_public": False},
    {"name": "shippingMethodUpdate", "kind": "MUTATION", "category": "shipping", "is_public": False},
    {"name": "shippingMethodDelete", "kind": "MUTATION", "category": "shipping", "is_public": False},
    # Payments
    {"name": "paymentInitialize", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentCapture", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentRefund", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentVoid", "kind": "MUTATION", "category": "payments", "is_public": False},
    # Discounts
    {"name": "saleCreate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "saleUpdate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "saleDelete", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "voucherCreate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "voucherUpdate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "voucherDelete", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionCreate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionUpdate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionDelete", "kind": "MUTATION", "category": "discounts", "is_public": False},
    # Warehouse
    {"name": "warehouseCreate", "kind": "MUTATION", "category": "warehouse", "is_public": False},
    {"name": "warehouseUpdate", "kind": "MUTATION", "category": "warehouse", "is_public": False},
    {"name": "warehouseDelete", "kind": "MUTATION", "category": "warehouse", "is_public": False},
    # Pages
    {"name": "pageCreate", "kind": "MUTATION", "category": "pages", "is_public": False},
    {"name": "pageUpdate", "kind": "MUTATION", "category": "pages", "is_public": False},
    {"name": "pageDelete", "kind": "MUTATION", "category": "pages", "is_public": False},
    # Shop
    {"name": "shopDomainUpdate", "kind": "MUTATION", "category": "shop", "is_public": False},
    {"name": "shopSettingsUpdate", "kind": "MUTATION", "category": "shop", "is_public": False},
    {"name": "shopAddressUpdate", "kind": "MUTATION", "category": "shop", "is_public": False},
    # Webhooks
    {"name": "webhookCreate", "kind": "MUTATION", "category": "webhooks", "is_public": False},
    {"name": "webhookUpdate", "kind": "MUTATION", "category": "webhooks", "is_public": False},
    {"name": "webhookDelete", "kind": "MUTATION", "category": "webhooks", "is_public": False},
    # Metadata
    {"name": "updateMetadata", "kind": "MUTATION", "category": "meta", "is_public": False},
    {"name": "deleteMetadata", "kind": "MUTATION", "category": "meta", "is_public": False},
    {"name": "updatePrivateMetadata", "kind": "MUTATION", "category": "meta", "is_public": False},
    {"name": "deletePrivateMetadata", "kind": "MUTATION", "category": "meta", "is_public": False},
]


def build_query(endpoint_name: str, kind: str) -> str:
    """Build a GraphQL query/mutation string for testing."""
    if kind == "QUERY":
        if endpoint_name == "shop":
            return 'query { shop { domain { host } version displayGrossPrices } }'
        elif endpoint_name == "products":
            return 'query { products(first: 3) { edges { node { id name slug } } pageInfo { hasNextPage endCursor } } }'
        elif endpoint_name == "categories":
            return 'query { categories(first: 3, level: 0) { edges { node { id name slug } } } }'
        elif endpoint_name == "collections":
            return 'query { collections(first: 3) { edges { node { id name slug } } } }'
        elif endpoint_name == "checkout":
            return 'query { checkout(token: "00000000-0000-0000-0000-000000000000") { id token } }'
        elif endpoint_name == "checkouts":
            return 'query { checkouts(first: 3) { edges { node { id token } } } }'
        elif endpoint_name == "orders":
            return 'query { orders(first: 3) { edges { node { id status } } } }'
        elif endpoint_name == "channels":
            return 'query { channels(first: 3) { edges { node { id name slug currencyCode isActive } } } }'
        elif endpoint_name == "shippingZones":
            return 'query { shippingZones(first: 3) { edges { node { id name countries } } } }'
        elif endpoint_name == "shippingMethods":
            return 'query { shippingZones(first: 1) { edges { node { shippingMethods { id name price { amount currency } } } } } }'
        elif endpoint_name == "attributes":
            return 'query { attributes(first: 3) { edges { node { id name slug } } } }'
        elif endpoint_name == "giftCards":
            return 'query { giftCards(first: 3) { edges { node { id isActive currentBalance { amount currency } } } } }'
        elif endpoint_name == "sales":
            return 'query { sales(first: 3) { edges { node { id name type startDate endDate } } } }'
        elif endpoint_name == "vouchers":
            return 'query { vouchers(first: 3) { edges { node { id name code discountValueType } } } }'
        elif endpoint_name == "promotions":
            return 'query { promotions(first: 3) { edges { node { id name startedAt endedAt } } } }'
        elif endpoint_name == "warehouses":
            return 'query { warehouses(first: 3) { edges { node { id name isPrimary } } } }'
        elif endpoint_name == "productTypes":
            return 'query { productTypes(first: 3) { edges { node { id name hasVariants isShippingRequired } } } }'
        elif endpoint_name == "plugins":
            return 'query { plugins(first: 3) { edges { node { id name active } } } }'
        elif endpoint_name == "webhookEvents":
            return 'query { webhookEvents { eventTypes { id name } } }'
        elif endpoint_name == "paymentGateways":
            return 'query { paymentGateways(first: 3) { id name } }'
        elif endpoint_name == "languages":
            return 'query { languages(first: 3) { code language } }'
        elif endpoint_name == "me":
            return 'query { me { id email firstName lastName } }'
        elif endpoint_name == "users":
            return 'query { users(first: 3) { edges { node { id email firstName lastName } } } }'
        elif endpoint_name == "ordersDraft":
            return 'query { ordersDraft(first: 3) { edges { node { id status } } } }'
        elif endpoint_name == "ordersByUser":
            return 'query { ordersByUser(first: 3) { edges { node { id status } } } }'
        elif endpoint_name == "product":
            return 'query { products(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "productType":
            return 'query { productTypes(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "category":
            return 'query { categories(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "collection":
            return 'query { collections(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "attribute":
            return 'query { attributes(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "giftCard":
            return 'query { giftCards(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "sale":
            return 'query { sales(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "voucher":
            return 'query { vouchers(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "channel":
            return 'query { channels(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "shippingZone":
            return 'query { shippingZones(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "warehouse":
            return 'query { warehouses(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "payment":
            return 'query { payments(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "page":
            return 'query { pages(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "pages":
            return 'query { pages(first: 3) { edges { node { id title slug } } } }'
        elif endpoint_name == "plugin":
            return 'query { plugins(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "order":
            return 'query { orders(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "user":
            return 'query { users(first: 1) { edges { node { id } } } }'
        elif endpoint_name == "permissionGroups":
            return 'query { permissionGroups(first: 3) { edges { node { id name } } } }'
        else:
            # Generic introspection query for unknown endpoints
            return f'query {{ {endpoint_name}(first: 1) {{ edges {{ node {{ id }} }} }} }}'

    elif kind == "MUTATION":
        # Mutations use dummy data — they may fail but we check for schema errors
        if endpoint_name == "checkoutCreate":
            return 'mutation { checkoutCreate(input: { channel: "default" }) { checkout { id } errors { field message code } } }'
        elif endpoint_name == "checkoutComplete":
            return 'mutation { checkoutComplete(id: "00000000-0000-0000-0000-000000000000") { order { id } errors { field message } } }'
        elif endpoint_name == "checkoutAddPromoCode":
            return 'mutation { checkoutAddPromoCode(id: "00000000-0000-0000-0000-000000000000", promoCode: "TEST") { checkout { id } errors { field message } } }'
        elif endpoint_name == "checkoutEmailUpdate":
            return 'mutation { checkoutEmailUpdate(id: "00000000-0000-0000-0000-000000000000", email: "test@test.com") { checkout { id } errors { field message } } }'
        elif endpoint_name == "accountRegister":
            return 'mutation { accountRegister(input: { email: "test@test.com", password: "Test1234!", channel: "default" }) { user { id email } errors { field message } } }'
        elif endpoint_name == "confirmAccount":
            return 'mutation { confirmAccount(email: "test@test.com", token: "testtoken") { user { id } errors { field message } } }'
        elif endpoint_name == "requestPasswordReset":
            return 'mutation { requestPasswordReset(email: "test@test.com", channel: "default") { errors { field message } } }'
        elif endpoint_name == "resetPassword":
            return 'mutation { resetPassword(token: "testtoken", password: "Test1234!") { user { id } errors { field message } } }'
        elif endpoint_name == "productCreate":
            return 'mutation { productCreate(input: { name: "Test", slug: "test-product-xyz", productType: "PHYSICAL" }) { product { id name } errors { field message code } } }'
        elif endpoint_name == "categoryCreate":
            return 'mutation { categoryCreate(input: { name: "Test Category", slug: "test-cat-xyz" }) { category { id name } errors { field message } } }'
        elif endpoint_name == "collectionCreate":
            return 'mutation { collectionCreate(input: { name: "Test Collection", slug: "test-col-xyz" }) { collection { id name } errors { field message } } }'
        elif endpoint_name == "channelCreate":
            return 'mutation { channelCreate(input: { name: "Test Channel", slug: "test-channel-xyz", currencyCode: "USD", isActive: true }) { channel { id name } errors { field message } } }'
        elif endpoint_name == "saleCreate":
            return 'mutation { saleCreate(input: { name: "Test Sale", type: PERCENTAGE, value: 10 }) { sale { id name } errors { field message } } }'
        elif endpoint_name == "voucherCreate":
            return 'mutation { voucherCreate(input: { code: "TESTXYZ", name: "Test Voucher", discountValueType: PERCENTAGE, discountValue: 10 }) { voucher { id code } errors { field message } } }'
        else:
            # Generic mutation with minimal args
            return f'mutation {{ {endpoint_name}(input: {{}}) {{ errors {{ field message code }} }} }}'


async def detect_saleor_version(url: str, token: str | None, timeout: int) -> str | None:
    """Try to detect Saleor version from shop query."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = '{"query":"query { shop { version } }"}'
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, data=query, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                version = data.get("data", {}).get("shop", {}).get("version")
                return version
    except Exception:
        pass
    return None


def build_endpoints_list(
    test_scope: str,
    public_only: bool = False,
    categories: list[str] | None = None,
) -> list[dict]:
    """Build the endpoint list for a test run from scope and filters."""
    if test_scope == "queries":
        endpoints = SALEOR_QUERIES.copy()
    elif test_scope == "mutations":
        endpoints = SALEOR_MUTATIONS.copy()
    elif test_scope == "custom" and categories:
        cats = set(categories)
        endpoints = [
            e
            for e in SALEOR_QUERIES + SALEOR_MUTATIONS
            if e["category"] in cats
        ]
    else:
        endpoints = SALEOR_QUERIES + SALEOR_MUTATIONS

    if public_only:
        endpoints = [e for e in endpoints if e["is_public"]]
    return endpoints


class TestRunner:
    """
    Core testing engine. Runs all tests against a Saleor endpoint
    and yields live progress events via an async generator.
    """

    def __init__(
        self,
        run_id: uuid.UUID,
        saleor_url: str,
        saleor_token: str | None,
        test_scope: str = "full",
        public_only: bool = False,
        concurrency: int = 5,
        timeout: int = 30,
        categories: list[str] | None = None,
        reference_saleor_url: str | None = None,
        reference_saleor_token: str | None = None,
        use_introspection: bool = True,
    ):
        self.run_id = run_id
        self.saleor_url = resolve_saleor_url_for_runner(saleor_url)
        self.saleor_token = saleor_token
        self.test_scope = test_scope
        self.public_only = public_only
        self.concurrency = concurrency
        self.timeout = timeout
        self.categories = categories
        self.reference_saleor_url = reference_saleor_url
        self.reference_saleor_token = reference_saleor_token
        self.use_introspection = use_introspection
        self._stopped = False

    def stop(self):
        self._stopped = True

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run all tests and yield progress events."""

        yield {"type": "progress", "message": "Detecting Saleor version…"}
        version = await detect_saleor_version(self.saleor_url, self.saleor_token, self.timeout)
        yield {"type": "version", "version": version}

        endpoints = build_endpoints_list(
            self.test_scope, self.public_only, self.categories
        )

        if self.use_introspection:
            yield {"type": "progress", "message": "Introspecting GraphQL schema…"}
            try:
                intro = await introspect_saleor(
                    self.saleor_url, self.saleor_token, self.timeout
                )
                ref_q = [e["name"] for e in SALEOR_QUERIES]
                ref_m = [e["name"] for e in SALEOR_MUTATIONS]
                diff = compare_schema(intro, ref_q, ref_m)
                yield {"type": "schema_diff", "diff": diff}

                known = {e["name"] for e in endpoints}
                for name in intro.get("queries", []):
                    if name not in known:
                        endpoints.append(
                            {
                                "name": name,
                                "kind": "QUERY",
                                "category": "unknown",
                                "is_public": True,
                            }
                        )
                        known.add(name)
                for name in intro.get("mutations", []):
                    if name not in known:
                        endpoints.append(
                            {
                                "name": name,
                                "kind": "MUTATION",
                                "category": "unknown",
                                "is_public": False,
                            }
                        )
                        known.add(name)

                if self.reference_saleor_url:
                    ref_intro = await introspect_saleor(
                        self.reference_saleor_url,
                        self.reference_saleor_token,
                        self.timeout,
                    )
                    ref_compare = compare_two_introspections(intro, ref_intro)
                    yield {
                        "type": "schema_diff",
                        "diff": {"reference_compare": ref_compare},
                    }
            except Exception as exc:
                yield {
                    "type": "schema_diff",
                    "diff": {"introspection_error": str(exc)},
                }

        total = len(endpoints)
        yield {
            "type": "progress",
            "message": f"Running {total} endpoint{'s' if total != 1 else ''}…",
            "total": total,
        }
        passed = failed = warnings = skipped = 0
        counts = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}

        semaphore = asyncio.Semaphore(self.concurrency)

        async def test_one(idx: int, endpoint: dict) -> dict:
            async with semaphore:
                if self._stopped:
                    return {
                        "status": "skip",
                        "endpoint": endpoint["name"],
                        "kind": endpoint["kind"],
                        "category": endpoint["category"],
                        "is_public": endpoint["is_public"],
                        "skipped": True,
                    }
                return await self._test_endpoint(endpoint, idx, total)

        tasks = [test_one(i, ep) for i, ep in enumerate(endpoints)]
        for coro in asyncio.as_completed(tasks):
            result = await coro

            status = result.get("status", "skip")
            if status == "pass":
                passed += 1
                counts["pass"] += 1
            elif status == "fail":
                failed += 1
                counts["fail"] += 1
            elif status == "warn":
                warnings += 1
                counts["warn"] += 1
            else:
                skipped += 1
                counts["skip"] += 1

            current = passed + failed + warnings + skipped
            yield {
                "type": "result",
                "run_id": str(self.run_id),
                "current": current,
                "total": total,
                "current_endpoint": result.get("endpoint", ""),
                "status": status,
                "endpoint_kind": result.get("kind", ""),
                "category": result.get("category", ""),
                "is_public": result.get("is_public", False),
                "response_time_ms": result.get("response_time_ms"),
                "error_message": result.get("error_message"),
                "input_sent": result.get("input_sent"),
                "actual_response": result.get("actual_response"),
                "saleor_field_type": result.get("saleor_field_type"),
                "actual_field_type": result.get("actual_field_type"),
                "status_counts": counts,
            }

        yield {
            "type": "complete",
            "run_id": str(self.run_id),
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "status_counts": counts,
        }

    async def _test_endpoint(self, endpoint: dict, idx: int, total: int) -> dict:
        """Test a single endpoint."""
        name = endpoint["name"]
        kind = endpoint["kind"]
        category = endpoint["category"]
        is_public = endpoint["is_public"]

        headers = {"Content-Type": "application/json"}
        if self.saleor_token:
            headers["Authorization"] = f"Bearer {self.saleor_token}"

        query = build_query(name, kind)
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.saleor_url,
                    data=json.dumps({"query": query}),
                    headers=headers,
                )
                elapsed_ms = int((time.time() - start) * 1000)

                resp_json = resp.json()

                # Check for GraphQL errors
                errors = resp_json.get("errors", [])
                if errors:
                    first_err = errors[0] if errors else {}
                    msg = first_err.get("message", "")
                    ext = first_err.get("extensions", {})
                    code = ext.get("code", "")

                    auth_codes = {
                        "permission",
                        "authentication",
                        "forbidden",
                        "jwt-error",
                        "jwt-invalid",
                        "PERMISSION_DENIED",
                    }
                    schema_markers = (
                        "cannot query",
                        "undefined type",
                        "field has unsupported",
                        "Unknown type",
                        "FieldUndefined",
                    )
                    validation_codes = {
                        "INVALID",
                        "GRAPHQL_VALIDATION_FAILED",
                        "REQUIRED",
                        "UNIQUE",
                    }

                    if code in auth_codes or str(code).lower() in auth_codes:
                        status = "warn"
                    elif any(m in msg.lower() for m in schema_markers):
                        status = "fail"
                    elif "not found" in msg.lower() or "does not exist" in msg.lower():
                        status = "pass"
                    elif code in validation_codes or kind == "MUTATION":
                        status = "warn"
                    else:
                        status = "pass"

                    return {
                        "status": status,
                        "endpoint": name,
                        "kind": kind,
                        "category": category,
                        "is_public": is_public,
                        "response_time_ms": elapsed_ms,
                        "error_message": msg if status != "pass" else None,
                        "input_sent": query,
                        "actual_response": json.dumps(resp_json),
                    }

                # No GraphQL errors — check HTTP status
                if resp.status_code != 200:
                    return {
                        "status": "fail",
                        "endpoint": name,
                        "kind": kind,
                        "category": category,
                        "is_public": is_public,
                        "response_time_ms": elapsed_ms,
                        "error_message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                        "input_sent": query,
                        "actual_response": resp.text[:500],
                    }

                # Success
                return {
                    "status": "pass",
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "response_time_ms": elapsed_ms,
                    "input_sent": query,
                    "actual_response": json.dumps(resp_json),
                }

        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "fail",
                "endpoint": name,
                "kind": kind,
                "category": category,
                "is_public": is_public,
                "response_time_ms": elapsed_ms,
                "error_message": f"Timeout after {self.timeout}s",
                "input_sent": query,
            }
        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "fail",
                "endpoint": name,
                "kind": kind,
                "category": category,
                "is_public": is_public,
                "response_time_ms": elapsed_ms,
                "error_message": f"HTTP {e.response.status_code}",
                "input_sent": query,
                "actual_response": e.response.text[:500],
            }
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "fail",
                "endpoint": name,
                "kind": kind,
                "category": category,
                "is_public": is_public,
                "response_time_ms": elapsed_ms,
                "error_message": str(e),
                "input_sent": query,
            }
