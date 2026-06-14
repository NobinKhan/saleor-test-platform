"""
Saleor demo topology seed — mutation-based populatedb-like fixtures for L3 probes.

Creates multi-channel, warehouse, customer, product, and order graphs via admin
GraphQL when DEMO_SEED_PROFILE=saleor_demo. Idempotent by slug/name lookup.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.reference_seed import (
    SeedResult,
    _append_mutation_errors,
    _capture_fixtures,
    _gql,
    _seed_storefront_fixtures,
    ensure_runtime_fixture_entities,
)

logger = logging.getLogger(__name__)

DEMO_CHANNEL_USD_SLUG = "default-channel"
DEMO_CHANNEL_PLN_SLUG = "channel-pln"
DEMO_PRODUCT_SLUG = "apple-juice"
DEMO_PRODUCT_NAME = "Apple Juice"

DEMO_WAREHOUSE_NAMES = (
    "Default Warehouse",
    "Default",
    "Europe",
    "Oceania",
    "Asia",
    "Americas",
    "Africa",
)

DEMO_CUSTOMERS: tuple[tuple[str, str, str], ...] = (
    ("ashley.cook@example.com", "Ashley", "Cook"),
    ("cassidy.villarreal@example.com", "Cassidy", "Villarreal"),
    ("crystal.miller@example.com", "Crystal", "Miller"),
    ("david.evans@example.com", "David", "Evans"),
    ("deborah.lee@example.com", "Deborah", "Lee"),
    ("dustin.gonzalez@example.com", "Dustin", "Gonzalez"),
    ("edward.cook@example.com", "Edward", "Cook"),
    ("garrett.cunningham@example.com", "Garrett", "Cunningham"),
    ("harness-reference-customer@example.com", "Harness", "Customer"),
    ("harness-storefront-customer@example.com", "Storefront", "Customer"),
)


async def _channel_by_slug(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    slug: str,
) -> dict[str, Any] | None:
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { channels { id slug name currencyCode } }",
        allow_errors=True,
    )
    for ch in data.get("channels") or []:
        if ch.get("slug") == slug:
            return ch
    return None


async def seed_demo_channels(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    specs = (
        (DEMO_CHANNEL_USD_SLUG, "Channel-USD", "USD", "US"),
        (DEMO_CHANNEL_PLN_SLUG, "Channel-PLN", "PLN", "PL"),
    )
    for slug, name, currency, country in specs:
        if await _channel_by_slug(client, url=url, headers=headers, slug=slug):
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: ChannelCreateInput!) { "
                "channelCreate(input: $input) { channel { id slug } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "name": name,
                    "slug": slug,
                    "currencyCode": currency,
                    "defaultCountry": country,
                    "isActive": True,
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="channelCreate",
        )
        payload = data.get("channelCreate")
        if (payload or {}).get("channel"):
            seeded.add(f"channel:{slug}")
        else:
            _append_mutation_errors(error_log, f"channelCreate({slug})", payload)

    usd = await _channel_by_slug(client, url=url, headers=headers, slug=DEMO_CHANNEL_USD_SLUG)
    if usd:
        fixtures["default_channel_id"] = usd["id"]
        fixtures["default_channel"] = usd.get("slug") or DEMO_CHANNEL_USD_SLUG
        seeded.add("default_channel_id")
    return seeded


async def _warehouse_by_name(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    name: str,
) -> dict[str, Any] | None:
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { warehouses(first: 50) { edges { node { id name } } } }",
        allow_errors=True,
    )
    for edge in (data.get("warehouses") or {}).get("edges") or []:
        node = edge.get("node") or {}
        if node.get("name") == name:
            return node
    return None


async def seed_demo_warehouses(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    for name in DEMO_WAREHOUSE_NAMES:
        if await _warehouse_by_name(client, url=url, headers=headers, name=name):
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: WarehouseCreateInput!) { "
                "warehouseCreate(input: $input) { warehouse { id name } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "name": name,
                    "address": {
                        "streetAddress1": "1 Demo St",
                        "city": "Demo City",
                        "postalCode": "00000",
                        "country": "US",
                    },
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="warehouseCreate",
        )
        payload = data.get("warehouseCreate")
        if (payload or {}).get("warehouse"):
            seeded.add(f"warehouse:{name}")
        else:
            _append_mutation_errors(error_log, f"warehouseCreate({name})", payload)

    default_wh = await _warehouse_by_name(
        client, url=url, headers=headers, name="Default Warehouse"
    )
    if default_wh:
        fixtures["default_warehouse_id"] = default_wh["id"]
        seeded.add("default_warehouse_id")
    return seeded


async def seed_demo_customers(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    for email, first_name, last_name in DEMO_CUSTOMERS:
        lookup = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "query($email: String!) { customers(first: 1, filter: {search: $email}) "
                "{ edges { node { id email } } } }"
            ),
            variables={"email": email},
            allow_errors=True,
        )
        edges = (lookup.get("customers") or {}).get("edges") or []
        if edges:
            if not fixtures.get("default_customer_id"):
                fixtures["default_customer_id"] = edges[0]["node"]["id"]
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: CustomerCreateInput!) { "
                "customerCreate(input: $input) { user { id email } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="customerCreate",
        )
        payload = data.get("customerCreate")
        user = (payload or {}).get("user")
        if user:
            seeded.add(f"customer:{email}")
            if not fixtures.get("default_customer_id"):
                fixtures["default_customer_id"] = user["id"]
        else:
            _append_mutation_errors(error_log, f"customerCreate({email})", payload)
    return seeded


async def _product_by_slug(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    slug: str,
    channel: str,
) -> dict[str, Any] | None:
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($slug: String!, $ch: String!) { "
            "product(slug: $slug, channel: $ch) { id slug variants { id sku } } }"
        ),
        variables={"slug": slug, "ch": channel},
        allow_errors=True,
    )
    return data.get("product")


async def seed_demo_product_variant(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    channel_slug = fixtures.get("default_channel") or DEMO_CHANNEL_USD_SLUG
    channel_id = fixtures.get("default_channel_id")
    product_type_id = fixtures.get("default_product_type_id")
    if not channel_id or not product_type_id:
        return seeded

    existing = await _product_by_slug(
        client, url=url, headers=headers, slug=DEMO_PRODUCT_SLUG, channel=channel_slug
    )
    if not existing:
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: ProductCreateInput!) { "
                "productCreate(input: $input) { product { id slug variants { id sku } } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "name": DEMO_PRODUCT_NAME,
                    "slug": DEMO_PRODUCT_SLUG,
                    "productType": product_type_id,
                    "channelListings": [{"channelId": channel_id, "isPublished": True}],
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="productCreate",
        )
        payload = data.get("productCreate")
        existing = (payload or {}).get("product")
        if existing:
            seeded.update({"default_product_id", "default_slug", "default_variant_id"})
        else:
            _append_mutation_errors(error_log, "productCreate(demo)", payload)
            return seeded

    if existing:
        fixtures["default_product_id"] = existing["id"]
        fixtures["default_slug"] = existing.get("slug") or DEMO_PRODUCT_SLUG
        variants = existing.get("variants") or []
        if not variants:
            vdata = await _gql(
                client,
                url=url,
                headers=headers,
                query=(
                    "mutation($pid: ID!, $input: ProductVariantCreateInput!) { "
                    "productVariantCreate(product: $pid, input: $input) { "
                    "productVariant { id sku } errors { field message code } } }"
                ),
                variables={
                    "pid": existing["id"],
                    "input": {"sku": "demo-apple-juice", "attributes": []},
                },
                allow_errors=True,
                error_log=error_log,
                operation="productVariantCreate",
            )
            vp = vdata.get("productVariantCreate")
            variant = (vp or {}).get("productVariant")
            if variant:
                variants = [variant]
                seeded.add("default_variant_id")
            else:
                _append_mutation_errors(error_log, "productVariantCreate", vp)
        if variants:
            fixtures["default_variant_id"] = variants[0]["id"]
            fixtures["variant_id_for_cart"] = variants[0]["id"]
            wh_id = fixtures.get("default_warehouse_id")
            if wh_id:
                await _gql(
                    client,
                    url=url,
                    headers=headers,
                    query=(
                        "mutation($variantId: ID!, $stocks: [StockInput!]!) { "
                        "productVariantStocksCreate(variantId: $variantId, stocks: $stocks) { "
                        "errors { field message code } } }"
                    ),
                    variables={
                        "variantId": variants[0]["id"],
                        "stocks": [{"warehouse": wh_id, "quantity": 500}],
                    },
                    allow_errors=True,
                    error_log=error_log,
                    operation="productVariantStocksCreate",
                )
                seeded.add("stock")
    return seeded


async def seed_demo_fulfillable_order(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    if fixtures.get("default_order_id"):
        return seeded
    channel_id = fixtures.get("default_channel_id")
    variant_id = fixtures.get("default_variant_id")
    customer_id = fixtures.get("default_customer_id")
    if not all([channel_id, variant_id, customer_id]):
        return seeded

    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: DraftOrderCreateInput!) { "
            "draftOrderCreate(input: $input) { order { id number } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "channelId": channel_id,
                "user": customer_id,
                "shippingMethod": None,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="draftOrderCreate",
    )
    payload = data.get("draftOrderCreate")
    order = (payload or {}).get("order")
    if not order:
        _append_mutation_errors(error_log, "draftOrderCreate", payload)
        return seeded

    order_id = order["id"]
    line_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $input: OrderLineCreateInput!) { "
            "orderLineCreate(id: $id, input: $input) { order { id } "
            "errors { field message code } } }"
        ),
        variables={"id": order_id, "input": {"variantId": variant_id, "quantity": 2}},
        allow_errors=True,
        error_log=error_log,
        operation="orderLineCreate",
    )
    if not (line_data.get("orderLineCreate") or {}).get("order"):
        _append_mutation_errors(error_log, "orderLineCreate", line_data.get("orderLineCreate"))

    complete = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!) { draftOrderComplete(id: $id) { order { id } "
            "errors { field message code } } }"
        ),
        variables={"id": order_id},
        allow_errors=True,
        error_log=error_log,
        operation="draftOrderComplete",
    )
    completed = (complete.get("draftOrderComplete") or {}).get("order")
    if completed:
        fixtures["default_order_id"] = completed["id"]
        seeded.add("default_order_id")
    else:
        fixtures["default_order_id"] = order_id
        seeded.add("default_order_id")
    return seeded


async def seed_search_isolation(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
) -> set[str]:
    """Ensure apple-juice unpublished search stays empty — unpublish if needed."""
    seeded: set[str] = set()
    channel_slug = fixtures.get("default_channel") or DEMO_CHANNEL_USD_SLUG
    channel_id = fixtures.get("default_channel_id")
    product_id = fixtures.get("default_product_id")
    if not product_id or not channel_id:
        return seeded
    await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $input: ProductChannelListingUpdateInput!) { "
            "productChannelListingUpdate(id: $id, input: $input) { "
            "errors { field message code } } }"
        ),
        variables={
            "id": product_id,
            "input": {"updateChannels": [{"channelId": channel_id, "isPublished": True}]},
        },
        allow_errors=True,
    )
    return seeded


async def ensure_saleor_demo_topology(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 120,
) -> SeedResult:
    """Create populatedb-like demo topology on target via admin mutations."""
    saleor_url = resolve_saleor_url_for_runner(saleor_url)
    seeded: set[str] = set()
    error_log: list[str] = []
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }

    base = await ensure_runtime_fixture_entities(saleor_url, token, timeout=timeout)
    seeded.update(base.seeded_keys)
    error_log.extend(base.errors)

    async with httpx.AsyncClient(timeout=timeout) as client:
        fixtures = await _capture_fixtures(client, url=saleor_url, headers=headers)
        fixtures.update(base.fixtures)

        seeded.update(
            await seed_demo_channels(
                client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
            )
        )
        seeded.update(
            await seed_demo_warehouses(
                client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
            )
        )
        seeded.update(
            await seed_demo_customers(
                client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
            )
        )
        seeded.update(
            await seed_demo_product_variant(
                client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
            )
        )
        seeded.update(
            await seed_demo_fulfillable_order(
                client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
            )
        )
        seeded.update(
            await seed_search_isolation(
                client, url=saleor_url, headers=headers, fixtures=fixtures
            )
        )
        fixtures = await _capture_fixtures(client, url=saleor_url, headers=headers)
        fixtures = await _seed_storefront_fixtures(
            client, url=saleor_url, headers=headers, fixtures=fixtures
        )

    live_keys = {k for k, v in fixtures.items() if v and k != "placeholder_id"}
    return SeedResult(
        fixtures=fixtures,
        live_keys=frozenset(live_keys),
        seeded_keys=frozenset(seeded),
        errors=tuple(error_log),
    )
