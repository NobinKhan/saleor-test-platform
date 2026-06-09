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

from app.core.config import settings
from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.version_routing import version_compatibility_warning
from app.services.reference_corpus import (
    load_all_probes_from_disk,
    load_manifest,
    resolve_corpus_version,
)
from app.services.introspection import compare_schema, introspect_saleor, schema_gate_diff
from app.services.saleor_auth import ensure_valid_token, refresh_saleor_token
from app.services.outcome import classify_graphql_response, classify_transport_error
from app.services.query_builder import build_query_with_schema, introspect_field_args
from app.services.client_bundle_fixtures import substitute_fixtures
from app.services.client_bundles import (
    build_client_bundle_endpoints,
    CLIENT_BUNDLE_KIND,
    load_all_bundles_from_disk,
    resolve_dashboard_bundle_version,
)
from app.services.client_bundle_schema_gate import (
    compute_client_bundle_schema_gate,
    merge_client_schema_into_diff,
)
from app.services.reference_compare import compare_to_golden, tier2_gate_enabled
from app.services.response_contract import CONTRACT_AUTH_ERROR, CONTRACT_SUCCESS, classify_response_contract

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
    {"name": "user", "kind": "QUERY", "category": "account", "is_public": False},
    {"name": "permissionGroups", "kind": "QUERY", "category": "account", "is_public": False},
    # Gift cards
    {"name": "giftCards", "kind": "QUERY", "category": "giftcards", "is_public": False},
    {"name": "giftCard", "kind": "QUERY", "category": "giftcards", "is_public": False},
    # Shipping
    {"name": "shippingZones", "kind": "QUERY", "category": "shipping", "is_public": True},
    {"name": "shippingZone", "kind": "QUERY", "category": "shipping", "is_public": True},
    # Payments
    {"name": "payments", "kind": "QUERY", "category": "payments", "is_public": False},
    {"name": "payment", "kind": "QUERY", "category": "payments", "is_public": False},
    # Discounts
    {"name": "vouchers", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "voucher", "kind": "QUERY", "category": "discounts", "is_public": True},
    {"name": "promotions", "kind": "QUERY", "category": "discounts", "is_public": True},
    # Warehouse
    {"name": "warehouses", "kind": "QUERY", "category": "warehouse", "is_public": False},
    {"name": "warehouse", "kind": "QUERY", "category": "warehouse", "is_public": False},
    # Shop
    {"name": "shop", "kind": "QUERY", "category": "shop", "is_public": True},
    # Pages
    {"name": "pages", "kind": "QUERY", "category": "pages", "is_public": True},
    {"name": "page", "kind": "QUERY", "category": "pages", "is_public": True},
    # Plugins
    {"name": "plugins", "kind": "QUERY", "category": "plugins", "is_public": False},
    {"name": "plugin", "kind": "QUERY", "category": "plugins", "is_public": False},
    # Webhooks
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
    {"name": "orderUpdate", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderConfirm", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderCancel", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderFulfill", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderRefund", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderLineDelete", "kind": "MUTATION", "category": "orders", "is_public": False},
    {"name": "orderLineUpdate", "kind": "MUTATION", "category": "orders", "is_public": False},
    # Checkout
    {"name": "checkoutCreate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutDelete", "kind": "MUTATION", "category": "checkout", "is_public": False},
    {"name": "checkoutComplete", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutAddPromoCode", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutRemovePromoCode", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutEmailUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
    {"name": "checkoutShippingAddressUpdate", "kind": "MUTATION", "category": "checkout", "is_public": True},
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
    # Payments
    {"name": "paymentInitialize", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentCapture", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentRefund", "kind": "MUTATION", "category": "payments", "is_public": False},
    {"name": "paymentVoid", "kind": "MUTATION", "category": "payments", "is_public": False},
    # Discounts
    {"name": "voucherCreate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "voucherUpdate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "voucherDelete", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionCreate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionUpdate", "kind": "MUTATION", "category": "discounts", "is_public": False},
    {"name": "promotionDelete", "kind": "MUTATION", "category": "discounts", "is_public": False},
    # Warehouse
    # Pages
    {"name": "pageCreate", "kind": "MUTATION", "category": "pages", "is_public": False},
    {"name": "pageUpdate", "kind": "MUTATION", "category": "pages", "is_public": False},
    {"name": "pageDelete", "kind": "MUTATION", "category": "pages", "is_public": False},
    # Shop
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

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                json={"query": "query { shop { version } }"},
                headers=headers,
            )
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
    elif test_scope == "catalog":
        endpoints = SALEOR_QUERIES + SALEOR_MUTATIONS
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


def build_golden_endpoints(
    corpus_version: str,
    test_scope: str,
    public_only: bool = False,
    categories: list[str] | None = None,
) -> list[dict]:
    """Build endpoint list from golden corpus probes for compatibility replay."""
    catalog_names = {e["name"] for e in SALEOR_QUERIES + SALEOR_MUTATIONS}
    probes = load_all_probes_from_disk(corpus_version)
    endpoints: list[dict] = []
    for probe in probes:
        if test_scope == "queries" and probe.endpoint_kind != "QUERY":
            continue
        if test_scope == "mutations" and probe.endpoint_kind != "MUTATION":
            continue
        if test_scope == "catalog" and probe.endpoint_name not in catalog_names:
            continue
        if test_scope == "custom" and categories and probe.category not in set(categories):
            continue
        is_public = probe.endpoint_name in {e["name"] for e in SALEOR_QUERIES if e["is_public"]}
        endpoints.append({
            "name": probe.endpoint_name,
            "kind": probe.endpoint_kind,
            "category": probe.category,
            "is_public": is_public,
            "golden_input": probe.input_sent,
        })
    if public_only:
        endpoints = [e for e in endpoints if e["is_public"]]
    return endpoints


def load_reference_schema(corpus_version: str) -> dict[str, list[str]]:
    """Reference schema from manifest or golden probe names."""
    manifest = load_manifest(corpus_version)
    if manifest:
        rq = manifest.get("reference_queries")
        rm = manifest.get("reference_mutations")
        if rq is not None and rm is not None:
            return {"queries": list(rq), "mutations": list(rm)}
    probes = load_all_probes_from_disk(corpus_version)
    return {
        "queries": sorted({p.endpoint_name for p in probes if p.endpoint_kind == "QUERY"}),
        "mutations": sorted({p.endpoint_name for p in probes if p.endpoint_kind == "MUTATION"}),
    }


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
        use_introspection: bool = True,
        test_mode: str = "compatibility",
        saleor_email: str | None = None,
        saleor_password: str | None = None,
        tier2_required: bool | None = None,
    ):
        self.run_id = run_id
        self.saleor_url = resolve_saleor_url_for_runner(saleor_url)
        self.saleor_token = saleor_token
        self.saleor_email = saleor_email
        self.saleor_password = saleor_password
        self.test_scope = test_scope
        self.public_only = public_only
        self.concurrency = concurrency
        self.timeout = timeout
        self.categories = categories
        self.use_introspection = use_introspection
        self.test_mode = test_mode if test_mode in ("compatibility", "discovery") else "compatibility"
        self.tier2_required = tier2_required
        self._stopped = False
        self.saleor_version: str | None = None
        self.schema_fields: dict[str, list[dict]] | None = None
        self.corpus_version: str | None = None

    def stop(self):
        self._stopped = True

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.saleor_token:
            headers["Authorization"] = f"Bearer {self.saleor_token}"
        return headers

    async def _ensure_valid_token(
        self,
        http_client: httpx.AsyncClient | None = None,
        *,
        force_refresh: bool = False,
    ) -> str | None:
        refreshed = await ensure_valid_token(
            saleor_url=self.saleor_url,
            token=self.saleor_token,
            email=self.saleor_email,
            password=self.saleor_password,
            timeout=self.timeout,
            client=http_client,
            force_refresh=force_refresh,
        )
        if refreshed:
            self.saleor_token = refreshed
        return self.saleor_token

    async def _force_refresh_token(self) -> str | None:
        if self.saleor_email and self.saleor_password:
            fresh, _err = await refresh_saleor_token(
                self.saleor_url,
                self.saleor_email,
                self.saleor_password,
                self.timeout,
            )
            if fresh:
                self.saleor_token = fresh
        return self.saleor_token

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run all tests and yield progress events."""

        yield {"type": "progress", "message": "Detecting Saleor version…"}
        version = await detect_saleor_version(self.saleor_url, self.saleor_token, self.timeout)
        self.saleor_version = version
        yield {"type": "version", "version": version}

        corpus_ver = resolve_corpus_version(version, settings.golden_corpus_version)
        self.corpus_version = corpus_ver
        ver_warn = version_compatibility_warning(version, corpus_ver)
        if ver_warn:
            yield {"type": "schema_diff", "diff": {"version_warning": ver_warn}}

        if self.test_mode == "compatibility":
            # Fixed certification L3 set from golden reference schema (not target introspection).
            certification_schema = load_reference_schema(corpus_ver)
            if self.test_scope == "client-dashboard":
                endpoints = build_client_bundle_endpoints(
                    recorded_only=True, schema_intro=certification_schema
                )
            elif self.test_scope == "full+client":
                endpoints = build_golden_endpoints(
                    corpus_ver, "full", self.public_only, self.categories
                )
                endpoints.extend(
                    build_client_bundle_endpoints(
                        recorded_only=True, schema_intro=certification_schema
                    )
                )
            else:
                endpoints = build_golden_endpoints(
                    corpus_ver, self.test_scope, self.public_only, self.categories
                )
        else:
            endpoints = build_endpoints_list(
                self.test_scope, self.public_only, self.categories
            )

        defer_schema = self.use_introspection and self.test_mode == "compatibility"
        if self.use_introspection and not defer_schema:
            yield {"type": "progress", "message": "Introspecting GraphQL schema…"}
            try:
                intro = await introspect_saleor(
                    self.saleor_url, self.saleor_token, self.timeout
                )
                try:
                    self.schema_fields = await introspect_field_args(
                        self.saleor_url, self.saleor_token, self.timeout
                    )
                except Exception:
                    self.schema_fields = None

                ref_q = [e["name"] for e in SALEOR_QUERIES]
                ref_m = [e["name"] for e in SALEOR_MUTATIONS]
                diff = compare_schema(intro, ref_q, ref_m)
                diff["schema_gate_source"] = "dashboard catalog"
                yield {"type": "schema_diff", "diff": diff}

                if self.test_mode == "discovery" and self.test_scope == "full":
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

        effective_concurrency = 1 if self.test_mode == "compatibility" else self.concurrency
        semaphore = asyncio.Semaphore(effective_concurrency)

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            if self.test_mode == "compatibility":
                yield {"type": "progress", "message": "Validating staff authentication…"}
                force = bool(self.saleor_email and self.saleor_password)
                await self._ensure_valid_token(http_client, force_refresh=force)
                if not self.saleor_token and force:
                    yield {
                        "type": "schema_diff",
                        "diff": {"introspection_error": "Staff authentication failed"},
                    }

            async def test_one(idx: int, endpoint: dict) -> dict:
                async with semaphore:
                    if self._stopped:
                        return {
                            "status": "skip",
                            "outcome": "skipped",
                            "expected": "Run stopped by user",
                            "response_valid": None,
                            "endpoint": endpoint["name"],
                            "kind": endpoint["kind"],
                            "category": endpoint["category"],
                            "is_public": endpoint["is_public"],
                            "skipped": True,
                        }
                    return await self._test_endpoint(endpoint, idx, total, http_client)

            async def emit_result(result: dict) -> dict:
                nonlocal passed, failed, warnings, skipped
                status = result.get("status", "skip")
                if self.test_mode == "compatibility":
                    if result.get("compatible"):
                        passed += 1
                        counts["pass"] += 1
                    elif result.get("match_status") == "missing_golden":
                        warnings += 1
                        counts["warn"] += 1
                    elif status == "skip":
                        skipped += 1
                        counts["skip"] += 1
                    else:
                        failed += 1
                        counts["fail"] += 1
                elif status == "pass":
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
                return {
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
                    "outcome": result.get("outcome"),
                    "expected": result.get("expected"),
                    "expected_response": result.get("expected_response"),
                    "match_status": result.get("match_status"),
                    "diff_summary": result.get("diff_summary"),
                    "client_parity_note": result.get("client_parity_note"),
                    "field_items": result.get("field_items"),
                    "compatible": result.get("compatible"),
                    "response_contract": result.get("response_contract"),
                    "response_valid": result.get("response_valid"),
                    "saleor_field_type": result.get("saleor_field_type"),
                    "actual_field_type": result.get("actual_field_type"),
                    "status_counts": counts,
                }

            if self.test_mode == "compatibility":
                for idx, endpoint in enumerate(endpoints):
                    yield await emit_result(await test_one(idx, endpoint))
            else:
                tasks = [test_one(i, ep) for i, ep in enumerate(endpoints)]
                for coro in asyncio.as_completed(tasks):
                    yield await emit_result(await coro)

        if defer_schema:
            yield {"type": "progress", "message": "Introspecting GraphQL schema (post-replay)…"}
            try:
                await self._ensure_valid_token(
                    force_refresh=bool(self.saleor_email and self.saleor_password),
                )
                intro = await introspect_saleor(
                    self.saleor_url, self.saleor_token, self.timeout
                )
                ref_schema = load_reference_schema(corpus_ver)
                diff = schema_gate_diff(intro, ref_schema, source="golden")
                if self.test_scope in ("client-dashboard", "full+client"):
                    dash_ver = resolve_dashboard_bundle_version()
                    bundles = load_all_bundles_from_disk(
                        "dashboard", dash_ver, recorded_only=True
                    )
                    client_gate = compute_client_bundle_schema_gate(
                        bundles, intro, recorded_only=True
                    )
                    diff = merge_client_schema_into_diff(diff, client_gate)
                yield {"type": "schema_diff", "diff": diff}
            except Exception as exc:
                yield {"type": "schema_diff", "diff": {"introspection_error": str(exc)}}

        yield {
            "type": "schema_diff",
            "diff": {"_run_meta": {"test_mode": self.test_mode}},
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
            "test_mode": self.test_mode,
        }

    async def _test_endpoint(
        self,
        endpoint: dict,
        idx: int,
        total: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> dict:
        """Test a single endpoint."""
        name = endpoint["name"]
        kind = endpoint["kind"]
        category = endpoint["category"]
        is_public = endpoint["is_public"]

        if self.test_mode == "compatibility" and endpoint.get("golden_input"):
            query = endpoint["golden_input"]
        else:
            query = build_query_with_schema(name, kind, self.schema_fields)
        payload: dict[str, Any] = {"query": query}
        if endpoint.get("bundle_document"):
            payload["query"] = endpoint["bundle_document"]
            variables = endpoint.get("bundle_variables") or {}
            fixtures = endpoint.get("bundle_fixtures") or {}
            try:
                payload["variables"] = substitute_fixtures(variables, fixtures)
            except KeyError:
                payload["variables"] = variables
        start = time.time()

        try:
            client = http_client or httpx.AsyncClient(timeout=self.timeout)
            own_client = http_client is None
            try:
                resp_json = {}
                resp_status = 500
                for attempt in range(3):
                    if self.test_mode == "compatibility" and (
                        not endpoint.get("is_public") or kind == CLIENT_BUNDLE_KIND
                    ):
                        await self._ensure_valid_token(client)
                    headers = self._auth_headers()
                    resp = await client.post(
                        self.saleor_url,
                        json=payload,
                        headers=headers,
                    )
                    resp_status = resp.status_code
                    resp_json = resp.json()
                    contract = classify_response_contract(resp_json, http_status=resp_status)
                    if contract != CONTRACT_AUTH_ERROR:
                        break
                    if attempt < 2:
                        await self._force_refresh_token()
                        await asyncio.sleep(0.25 * (attempt + 1))
                elapsed_ms = int((time.time() - start) * 1000)

                meta = classify_graphql_response(
                    resp_json,
                    http_status=resp_status,
                    endpoint_kind=kind,
                )
                comparison = compare_to_golden(
                    self.saleor_version,
                    name,
                    kind,
                    resp_json,
                    meta,
                    http_status=resp_status,
                    tier2_required=tier2_gate_enabled(self.tier2_required),
                )
                if self.test_mode == "compatibility":
                    status = "pass" if comparison.compatible else (
                        "warn" if comparison.match_status == "missing_golden" else "fail"
                    )
                else:
                    status = comparison.recommended_status
                    if comparison.match_status == "missing_golden":
                        status = meta["status"]
                contract = meta.get("response_contract") or comparison.actual_contract
                expected_label = (
                    f"Contract: {comparison.golden_contract or '?'} → {comparison.actual_contract or contract}"
                    if comparison.golden_contract
                    else meta["expected"]
                )
                return {
                    "status": status,
                    "outcome": comparison.actual_contract or meta.get("response_contract") or meta["outcome"],
                    "expected": expected_label,
                    "expected_response": comparison.expected_response,
                    "match_status": comparison.match_status,
                    "diff_summary": comparison.diff_summary,
                    "client_parity_note": comparison.client_parity_note,
                    "field_items": comparison.field_items,
                    "compatible": comparison.compatible,
                    "response_contract": contract,
                    "response_valid": meta["response_valid"],
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "response_time_ms": elapsed_ms,
                    "error_message": meta.get("error_message"),
                    "input_sent": json.dumps(payload) if endpoint.get("bundle_document") else query,
                    "actual_response": json.dumps(resp_json),
                }
            finally:
                if own_client:
                    await client.aclose()

        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(
                kind="timeout",
                message=f"Timeout after {self.timeout}s",
            )
            return _result_from_meta(meta, name, kind, category, is_public, elapsed_ms, query)
        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(
                kind="http",
                message=f"HTTP {e.response.status_code}",
            )
            return _result_from_meta(
                meta, name, kind, category, is_public, elapsed_ms, query,
                actual_response=e.response.text[:500],
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(kind="error", message=str(e))
            return _result_from_meta(meta, name, kind, category, is_public, elapsed_ms, query)


def _result_from_meta(
    meta: dict,
    name: str,
    kind: str,
    category: str,
    is_public: bool,
    elapsed_ms: int,
    query: str,
    actual_response: str | None = None,
) -> dict:
    return {
        "status": meta["status"],
        "outcome": meta["outcome"],
        "expected": meta["expected"],
        "response_valid": meta["response_valid"],
        "endpoint": name,
        "kind": kind,
        "category": category,
        "is_public": is_public,
        "response_time_ms": elapsed_ms,
        "error_message": meta.get("error_message"),
        "input_sent": query,
        "actual_response": actual_response,
    }
