"""
Seed minimal reference data on official Saleor for L3 fixture capture.

Uses populatedb/demo data when present; creates harness-reference entities only for
missing fixture keys required by L3 dashboard bundles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.client_bundles import save_fixtures

REFERENCE_PRODUCT_SLUG = "harness-reference-product"
REFERENCE_PRODUCT_TYPE_SLUG = "harness-reference-type"
REFERENCE_CHANNEL_SLUG = "harness-channel"
REFERENCE_COLLECTION_SLUG = "harness-reference-collection"
REFERENCE_CUSTOMER_EMAIL = "harness-reference-customer@example.com"

REQUIRED_FIXTURE_KEYS = (
    "default_channel_id",
    "default_product_id",
    "default_variant_id",
    "default_customer_id",
    "default_collection_id",
    "default_order_id",
)

STOREFRONT_FIXTURE_KEYS = (
    "default_checkout_id",
    "default_checkout_token",
    "variant_id_for_cart",
    "storefront_customer_id",
)


CATALOG_CATEGORY_SPECS: tuple[tuple[str, str], ...] = (
    ("Harness Default Category", "default-category"),
    ("Harness Accessories", "accessories"),
)


async def _ensure_catalog_categories(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Idempotent category tree for search/homepage L3 bundles."""
    seeded: set[str] = set()
    for name, slug in CATALOG_CATEGORY_SPECS:
        existing = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "query($slug: String!) { category(slug: $slug) { id slug } }"
            ),
            variables={"slug": slug},
            allow_errors=True,
        )
        if (existing.get("category") or {}).get("id"):
            if slug == "default-category":
                fixtures["default_category_id"] = existing["category"]["id"]
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: CategoryInput!) { "
                "categoryCreate(input: $input) { category { id slug } "
                "errors { field message code } } }"
            ),
            variables={"input": {"name": name, "slug": slug}},
            allow_errors=True,
            error_log=error_log,
            operation="categoryCreate",
        )
        category = (data.get("categoryCreate") or {}).get("category")
        if category:
            seeded.add(f"category:{slug}")
            if slug == "default-category":
                fixtures["default_category_id"] = category["id"]
                fixtures["default_slug"] = slug
    return seeded


async def ensure_certification_topology(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 120,
    full_topology: bool = False,
) -> SeedResult:
    """Mutation-first fixture topology for L3 certification runs."""
    if full_topology:
        from app.services.demo_seed import ensure_saleor_demo_topology

        return await ensure_saleor_demo_topology(
            saleor_url, token, timeout=max(timeout, 120)
        )

    saleor_url = resolve_saleor_url_for_runner(saleor_url)
    result = await ensure_runtime_fixture_entities(saleor_url, token, timeout=timeout)

    error_log = list(result.errors)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }
    fixtures = dict(result.fixtures)
    seeded = set(result.seeded_keys)

    async with httpx.AsyncClient(timeout=timeout) as client:
        from app.services.demo_seed import seed_demo_fulfillable_order

        if not fixtures.get("default_order_id"):
            seeded.update(
                await seed_demo_fulfillable_order(
                    client,
                    url=saleor_url,
                    headers=headers,
                    fixtures=fixtures,
                    error_log=error_log,
                )
            )
        seeded.update(
            await _ensure_catalog_categories(
                client,
                url=saleor_url,
                headers=headers,
                fixtures=fixtures,
                error_log=error_log,
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


@dataclass(frozen=True)
class SeedResult:
    fixtures: dict[str, Any]
    live_keys: frozenset[str] = field(default_factory=frozenset)
    seeded_keys: frozenset[str] = field(default_factory=frozenset)
    errors: tuple[str, ...] = ()


def _append_mutation_errors(
    errors: list[str],
    operation: str,
    payload: dict[str, Any] | None,
) -> None:
    if not payload:
        errors.append(f"{operation}: no data returned")
        return
    for err in payload.get("errors") or []:
        if not isinstance(err, dict):
            errors.append(f"{operation}: {err}")
            continue
        field_name = err.get("field") or "root"
        message = err.get("message") or err.get("code") or str(err)
        errors.append(f"{operation} ({field_name}): {message}")


async def _gql(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    query: str,
    variables: dict[str, Any] | None = None,
    allow_errors: bool = False,
    error_log: list[str] | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = await client.post(url, json=payload, headers=headers)
    body = resp.json()
    if error_log is not None:
        for err in body.get("errors") or []:
            if isinstance(err, dict):
                error_log.append(f"{operation or 'GraphQL'}: {err.get('message', err)}")
            else:
                error_log.append(f"{operation or 'GraphQL'}: {err}")
    if body.get("errors") and not allow_errors:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body.get("data") or {}


async def _capture_fixtures(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    """Read fixture IDs from the target Saleor (no mutations).

    Uses intelligent discovery: tries to find entities that match expected
    characteristics (published products with variants, multi-channel setup),
    falls back to first available entity if no match found.
    """
    fixtures: dict[str, Any] = {
        "default_channel": "default-channel",
        "default_slug": "test-product",
        "placeholder_id": "00000000-0000-0000-0000-000000000000",
    }

    # ── Channels ─────────────────────────────────────────────────────────
    ch_data = await _gql(
        client, url=url, headers=headers, query="query { channels { id slug isActive } }"
    )
    channels = ch_data.get("channels") or []
    if channels:
        # Prefer the default-channel or first active channel
        preferred = None
        for ch in channels:
            if ch.get("slug") == "default-channel" and ch.get("isActive"):
                preferred = ch
                break
        if not preferred:
            for ch in channels:
                if ch.get("isActive"):
                    preferred = ch
                    break
        if not preferred:
            preferred = channels[0]
        fixtures["default_channel"] = preferred.get("slug") or fixtures["default_channel"]
        fixtures["default_channel_id"] = preferred.get("id")

    # ── Products ─────────────────────────────────────────────────────────
    ch = fixtures["default_channel"]
    # Try to find a published product with variants (best candidate for probing)
    prod_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($ch: String!) { products(first: 5, channel: $ch) "
            "{ edges { node { id slug variants { id name } "
            "productType { id } channelListings { channel { slug } isPublished } "
            "} } } }"
        ),
        variables={"ch": ch},
        allow_errors=True,
    )
    edges = (prod_data.get("products") or {}).get("edges") or []

    def _published_on_channel(node: dict[str, Any], channel_slug: str) -> bool:
        for listing in node.get("channelListings") or []:
            ch_info = listing.get("channel") or {}
            if ch_info.get("slug") == channel_slug and listing.get("isPublished"):
                return True
        return False

    # Pick the best candidate: published on default channel with variants
    best_product = None
    for edge in edges:
        node = edge.get("node") or {}
        if _published_on_channel(node, ch) and node.get("variants"):
            best_product = node
            break
    if not best_product and edges:
        best_product = edges[0].get("node") or {}

    if best_product:
        fixtures["default_slug"] = best_product.get("slug") or fixtures["default_slug"]
        fixtures["default_product_id"] = best_product.get("id")
        variants = best_product.get("variants") or []
        if variants:
            fixtures["default_variant_id"] = variants[0].get("id")
        pt = best_product.get("productType") or {}
        if pt.get("id"):
            fixtures["default_product_type_id"] = pt["id"]

    # ── Product Type (fallback) ──────────────────────────────────────────
    if not fixtures.get("default_product_type_id"):
        pt_data = await _gql(
            client, url=url, headers=headers,
            query="query { productTypes(first: 1) { edges { node { id } } } }",
            allow_errors=True,
        )
        pt_edges = (pt_data.get("productTypes") or {}).get("edges") or []
        if pt_edges:
            fixtures["default_product_type_id"] = pt_edges[0]["node"]["id"]

    # ── Other entities ───────────────────────────────────────────────────
    for query_name, key in (
        ("orders(first: 1)", "default_order_id"),
        ("customers(first: 1)", "default_customer_id"),
        ("categories(first: 1)", "default_category_id"),
    ):
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=f"query {{ {query_name} {{ edges {{ node {{ id }} }} }} }}",
            allow_errors=True,
        )
        root = query_name.split("(")[0]
        edges = (data.get(root) or {}).get("edges") or []
        if edges:
            fixtures[key] = edges[0]["node"]["id"]
            # storefront_customer_id is the same as default_customer_id
            if key == "default_customer_id":
                fixtures["storefront_customer_id"] = edges[0]["node"]["id"]

    # ── Collections ──────────────────────────────────────────────────────
    coll_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($ch: String!) { collections(first: 3, channel: $ch) "
            "{ edges { node { id name slug } } } }"
        ),
        variables={"ch": ch},
        allow_errors=True,
    )
    coll_edges = (coll_data.get("collections") or {}).get("edges") or []
    if coll_edges:
        # Prefer a collection with a recognizable name
        best_coll = coll_edges[0].get("node") or {}
        for edge in coll_edges:
            node = edge.get("node") or {}
            name = (node.get("name") or "").lower()
            if "featured" in name or "default" in name:
                best_coll = node
                break
        fixtures["default_collection_id"] = best_coll.get("id")

    return fixtures


async def capture_live_fixtures(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 60,
) -> dict[str, Any]:
    """Read fixture IDs from the target Saleor (no mutations)."""
    saleor_url = resolve_saleor_url_for_runner(saleor_url)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await _capture_fixtures(client, url=saleor_url, headers=headers)


async def _ensure_channel(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    if fixtures.get("default_channel_id"):
        return False
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
                "name": "Harness Channel",
                "slug": REFERENCE_CHANNEL_SLUG,
                "currencyCode": "USD",
                "defaultCountry": "US",
                "isActive": True,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="channelCreate",
    )
    payload = data.get("channelCreate")
    channel = (payload or {}).get("channel")
    if channel:
        fixtures["default_channel_id"] = channel["id"]
        fixtures["default_channel"] = channel.get("slug") or REFERENCE_CHANNEL_SLUG
        return True
    _append_mutation_errors(error_log, "channelCreate", payload)
    return False


async def _ensure_product_type(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    if fixtures.get("default_product_type_id"):
        return False
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: ProductTypeInput!) { "
            "productTypeCreate(input: $input) { productType { id slug } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "name": "Harness Reference Type",
                "slug": REFERENCE_PRODUCT_TYPE_SLUG,
                "hasVariants": True,
                "isShippingRequired": True,
                "weight": 1,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="productTypeCreate",
    )
    payload = data.get("productTypeCreate")
    product_type = (payload or {}).get("productType")
    if product_type:
        fixtures["default_product_type_id"] = product_type["id"]
        return True
    _append_mutation_errors(error_log, "productTypeCreate", payload)
    return False


async def _ensure_reference_product(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    if fixtures.get("default_product_id") and fixtures.get("default_variant_id"):
        return False
    channel_id = fixtures.get("default_channel_id")
    channel_slug = fixtures.get("default_channel")
    product_type_id = fixtures.get("default_product_type_id")
    if not channel_id or not product_type_id:
        return False

    by_slug = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($slug: String!) { "
            "product(slug: $slug) { id slug variants { id } channelListings { channel { id } } } }"
        ),
        variables={"slug": REFERENCE_PRODUCT_SLUG},
        allow_errors=True,
        error_log=error_log,
        operation="productBySlug",
    )
    existing = by_slug.get("product")
    if existing and existing.get("id"):
        fixtures["default_product_id"] = existing["id"]
        fixtures["default_slug"] = existing.get("slug") or REFERENCE_PRODUCT_SLUG
        variants = existing.get("variants") or []
        if variants:
            variant_id = variants[0]["id"]
            fixtures["default_variant_id"] = variant_id
            fixtures["variant_id_for_cart"] = variant_id
            # Ensure product is assigned to channel with variant available for purchase
            channel_listings = existing.get("channelListings") or []
            if not any(cl.get("channel", {}).get("id") == channel_id for cl in channel_listings):
                # Assign category first (required for publishing)
                category_id = fixtures.get("default_category_id")
                if category_id:
                    await _gql(
                        client,
                        url=url,
                        headers=headers,
                        query=(
                            "mutation($id: ID!, $input: ProductUpdateInput!) { "
                            "productUpdate(id: $id, input: $input) { product { id } "
                            "errors { field message code } } }"
                        ),
                        variables={
                            "id": existing["id"],
                            "input": {"category": category_id},
                        },
                        allow_errors=True,
                        error_log=error_log,
                        operation="productUpdate(category)",
                    )
                await _gql(
                    client,
                    url=url,
                    headers=headers,
                    query=(
                        "mutation($id: ID!, $input: ProductChannelListingUpdateInput!) { "
                        "productChannelListingUpdate(id: $id, input: $input) { product { id } "
                        "errors { field message code } } }"
                    ),
                    variables={
                        "id": existing["id"],
                        "input": {
                            "updateChannels": [{
                                "channelId": channel_id,
                                "isPublished": True,
                                "isAvailableForPurchase": True,
                                "addVariants": [variant_id],
                            }],
                        },
                    },
                    allow_errors=True,
                    error_log=error_log,
                    operation="productChannelListingUpdate",
                )
                # Set variant price
                await _gql(
                    client,
                    url=url,
                    headers=headers,
                    query=(
                        "mutation($id: ID!, $input: [ProductVariantChannelListingAddInput!]!) { "
                        "productVariantChannelListingUpdate(id: $id, input: $input) { variant { id } "
                        "errors { field message code } } }"
                    ),
                    variables={
                        "id": variant_id,
                        "input": [{"channelId": channel_id, "price": "10.00"}],
                    },
                    allow_errors=True,
                    error_log=error_log,
                    operation="productVariantChannelListingUpdate",
                )
                # Create stock
                warehouse_data = await _gql(
                    client,
                    url=url,
                    headers=headers,
                    query="query { warehouses(first: 1) { edges { node { id } } } }",
                    allow_errors=True,
                    error_log=error_log,
                    operation="warehouses",
                )
                warehouses = (warehouse_data.get("warehouses") or {}).get("edges") or []
                if warehouses:
                    wh_id = warehouses[0]["node"]["id"]
                    await _gql(
                        client,
                        url=url,
                        headers=headers,
                        query=(
                            "mutation($variantId: ID!, $stocks: [StockInput!]!) { "
                            "productVariantStocksCreate(variantId: $variantId, stocks: $stocks) "
                            "{ productVariant { id } errors { field message code } } }"
                        ),
                        variables={
                            "variantId": variant_id,
                            "stocks": [{"warehouse": wh_id, "quantity": 100}],
                        },
                        allow_errors=True,
                        error_log=error_log,
                        operation="productVariantStocksCreate",
                    )
                # Also assign to storefront channel (channel-pln)
                pln_data = await _gql(
                    client,
                    url=url,
                    headers=headers,
                    query="query { channels { id slug isActive } }",
                    allow_errors=True,
                    error_log=error_log,
                    operation="channels",
                )
                for ch in (pln_data.get("channels") or []):
                    if ch.get("slug") == "channel-pln" and ch.get("isActive") and ch.get("id") != channel_id:
                        pln_id = ch["id"]
                        await _gql(
                            client, url=url, headers=headers,
                            query=(
                                "mutation($id: ID!, $input: ProductChannelListingUpdateInput!) { "
                                "productChannelListingUpdate(id: $id, input: $input) { product { id } "
                                "errors { field message code } } }"
                            ),
                            variables={"id": existing["id"], "input": {"updateChannels": [{"channelId": pln_id, "isPublished": True, "isAvailableForPurchase": True, "addVariants": [variant_id]}]}},
                            allow_errors=True, error_log=error_log, operation="productChannelListingUpdate(pln)",
                        )
                        await _gql(
                            client, url=url, headers=headers,
                            query=(
                                "mutation($id: ID!, $input: [ProductVariantChannelListingAddInput!]!) { "
                                "productVariantChannelListingUpdate(id: $id, input: $input) { variant { id } "
                                "errors { field message code } } }"
                            ),
                            variables={"id": variant_id, "input": [{"channelId": pln_id, "price": "10.00"}]},
                            allow_errors=True, error_log=error_log, operation="productVariantChannelListingUpdate(pln)",
                        )
                        break
            return True

    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: ProductCreateInput!) { "
            "productCreate(input: $input) { product { id slug variants { id } } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "name": "Harness Reference Product",
                "slug": REFERENCE_PRODUCT_SLUG,
                "productType": product_type_id,
                "category": fixtures.get("default_category_id"),
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="productCreate",
    )
    create_payload = data.get("productCreate")
    product = (create_payload or {}).get("product")
    if not product:
        _append_mutation_errors(error_log, "productCreate", create_payload)
        return False
    fixtures["default_product_id"] = product["id"]
    fixtures["default_slug"] = product.get("slug") or REFERENCE_PRODUCT_SLUG

    # Create variant first (if not returned by productCreate)
    variants = product.get("variants") or []
    variant_id = variants[0]["id"] if variants else None

    if not variant_id:
        variant_data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: ProductVariantCreateInput!) { "
                "productVariantCreate(input: $input) { productVariant { id } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "product": product["id"],
                    "sku": "harness-ref-sku",
                    "attributes": [],
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="productVariantCreate",
        )
        variant_payload = variant_data.get("productVariantCreate")
        variant = (variant_payload or {}).get("productVariant")
        if variant:
            variant_id = variant["id"]
        else:
            _append_mutation_errors(error_log, "productVariantCreate", variant_payload)
            return False

    # Assign product to channel with variant (Saleor 3.23.7 uses productChannelListingUpdate)
    # Include addVariants and isAvailableForPurchase so variant is available for purchase
    await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $input: ProductChannelListingUpdateInput!) { "
            "productChannelListingUpdate(id: $id, input: $input) { product { id } "
            "errors { field message code } } }"
        ),
        variables={
            "id": product["id"],
            "input": {
                "updateChannels": [{
                    "channelId": channel_id,
                    "isPublished": True,
                    "isAvailableForPurchase": True,
                    "addVariants": [variant_id],
                }],
            },
        },
        allow_errors=True,
        error_log=error_log,
        operation="productChannelListingUpdate",
    )

    # Set price on variant channel listing (required for checkout)
    await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $input: [ProductVariantChannelListingAddInput!]!) { "
            "productVariantChannelListingUpdate(id: $id, input: $input) { variant { id } "
            "errors { field message code } } }"
        ),
        variables={
            "id": variant_id,
            "input": [{"channelId": channel_id, "price": "10.00"}],
        },
        allow_errors=True,
        error_log=error_log,
        operation="productVariantChannelListingUpdate",
    )

    # Also assign product to storefront channel (channel-pln) if it exists
    pln_data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { channels { id slug isActive } }",
        allow_errors=True,
        error_log=error_log,
        operation="channels",
    )
    all_channels = (pln_data.get("channels") or [])
    pln_channel = None
    for ch in all_channels:
        if ch.get("slug") == "channel-pln" and ch.get("isActive"):
            pln_channel = ch
            break
    if pln_channel and pln_channel.get("id") != channel_id:
        pln_id = pln_channel["id"]
        await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $input: ProductChannelListingUpdateInput!) { "
                "productChannelListingUpdate(id: $id, input: $input) { product { id } "
                "errors { field message code } } }"
            ),
            variables={
                "id": product["id"],
                "input": {
                    "updateChannels": [{
                        "channelId": pln_id,
                        "isPublished": True,
                        "isAvailableForPurchase": True,
                        "addVariants": [variant_id],
                    }],
                },
            },
            allow_errors=True,
            error_log=error_log,
            operation="productChannelListingUpdate(pln)",
        )
        await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $input: [ProductVariantChannelListingAddInput!]!) { "
                "productVariantChannelListingUpdate(id: $id, input: $input) { variant { id } "
                "errors { field message code } } }"
            ),
            variables={
                "id": variant_id,
                "input": [{"channelId": pln_id, "price": "10.00"}],
            },
            allow_errors=True,
            error_log=error_log,
            operation="productVariantChannelListingUpdate(pln)",
        )

    # Create stock for variant in the first warehouse
    warehouse_data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { warehouses(first: 1) { edges { node { id } } } }",
        allow_errors=True,
        error_log=error_log,
        operation="warehouses",
    )
    warehouses = (warehouse_data.get("warehouses") or {}).get("edges") or []
    if warehouses:
        wh_id = warehouses[0]["node"]["id"]
        await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($variantId: ID!, $stocks: [StockInput!]!) { "
                "productVariantStocksCreate(variantId: $variantId, stocks: $stocks) "
                "{ productVariant { id } errors { field message code } } }"
            ),
            variables={
                "variantId": variant_id,
                "stocks": [{"warehouse": wh_id, "quantity": 100}],
            },
            allow_errors=True,
            error_log=error_log,
            operation="productVariantStocksCreate",
        )

    fixtures["default_variant_id"] = variant_id
    fixtures["variant_id_for_cart"] = variant_id
    return True


async def _ensure_customer_and_collection(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
) -> set[str]:
    seeded: set[str] = set()
    channel_id = fixtures.get("default_channel_id")
    if not fixtures.get("default_customer_id"):
        create_cust = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: UserCreateInput!) { "
                "customerCreate(input: $input) { user { id email } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "email": REFERENCE_CUSTOMER_EMAIL,
                    "firstName": "Harness",
                    "lastName": "Reference",
                }
            },
            allow_errors=True,
        )
        user = (create_cust.get("customerCreate") or {}).get("user")
        if user:
            fixtures["default_customer_id"] = user["id"]
            fixtures["storefront_customer_id"] = user["id"]
            seeded.add("default_customer_id")

    if channel_id and not fixtures.get("default_collection_id"):
        # First check if collection exists by slug
        existing_coll = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "query($slug: String!) { "
                "collection(slug: $slug) { id slug channelListings { channel { id } } } }"
            ),
            variables={"slug": REFERENCE_COLLECTION_SLUG},
            allow_errors=True,
        )
        coll_data = existing_coll.get("collection")
        if coll_data and coll_data.get("id"):
            fixtures["default_collection_id"] = coll_data["id"]
            seeded.add("default_collection_id")
        else:
            create_coll = await _gql(
                client,
                url=url,
                headers=headers,
                query=(
                    "mutation($input: CollectionCreateInput!) { "
                    "collectionCreate(input: $input) { collection { id } "
                    "errors { field message code } } }"
                ),
                variables={
                    "input": {
                        "name": "Harness Reference Collection",
                        "slug": REFERENCE_COLLECTION_SLUG,
                        "isPublished": True,
                    }
                },
                allow_errors=True,
            )
            coll = (create_coll.get("collectionCreate") or {}).get("collection")
            if coll:
                fixtures["default_collection_id"] = coll["id"]
                seeded.add("default_collection_id")

    if fixtures.get("default_collection_id") and fixtures.get("default_product_id"):
        await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $products: [ID!]!) { "
                "collectionAddProducts(collectionId: $id, products: $products) { "
                "errors { field message code } } }"
            ),
            variables={
                "id": fixtures["default_collection_id"],
                "products": [fixtures["default_product_id"]],
            },
            allow_errors=True,
        )
    return seeded


REFERENCE_CATEGORY_SLUG = "harness-reference-category"
REFERENCE_WAREHOUSE_SLUG = "harness-reference-warehouse"


async def _ensure_category(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    """Create a category if none exists."""
    if fixtures.get("default_category_id"):
        return False
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: CategoryInput!) { "
            "categoryCreate(input: $input) { category { id } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "name": "Harness Reference Category",
                "slug": REFERENCE_CATEGORY_SLUG,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="categoryCreate",
    )
    payload = data.get("categoryCreate")
    category = (payload or {}).get("category")
    if category:
        fixtures["default_category_id"] = category["id"]
        return True
    _append_mutation_errors(error_log, "categoryCreate", payload)
    return False


async def _ensure_warehouse(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    """Create a warehouse assigned to all active channels."""
    if fixtures.get("default_warehouse_id"):
        return False
    channel_id = fixtures.get("default_channel_id")
    if not channel_id:
        return False
    # Discover all channels to assign warehouse to all of them
    ch_data = await _gql(
        client, url=url, headers=headers,
        query="query { channels { id slug isActive } }",
        allow_errors=True, error_log=error_log, operation="channels",
    )
    all_channel_ids = [ch["id"] for ch in (ch_data.get("channels") or []) if ch.get("isActive")]
    if not all_channel_ids:
        all_channel_ids = [channel_id]
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: WarehouseCreateInput!) { "
            "warehouseCreate(input: $input) { warehouse { id } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "name": "Harness Reference Warehouse",
                "slug": REFERENCE_WAREHOUSE_SLUG,
                "email": "warehouse@example.com",
                "channels": all_channel_ids,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="warehouseCreate",
    )
    payload = data.get("warehouseCreate")
    warehouse = (payload or {}).get("warehouse")
    if warehouse:
        fixtures["default_warehouse_id"] = warehouse["id"]
        return True
    _append_mutation_errors(error_log, "warehouseCreate", payload)
    return False


async def _ensure_order(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> bool:
    """Create a draft order with line items and complete it.

    The order needs to exist for L3 dashboard bundles that query or mutate
    orders (e.g., orderRefundData, fulfillOrder, orderNoteAdd).
    """
    if fixtures.get("default_order_id"):
        return False

    channel_id = fixtures.get("default_channel_id")
    variant_id = fixtures.get("default_variant_id")
    customer_id = fixtures.get("default_customer_id")
    if not channel_id or not variant_id:
        return False

    # Ensure a permission group with channel access exists (Saleor 3.23.7 requires this)
    # Get admin user ID
    me_data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { me { id } }",
        allow_errors=True,
        error_log=error_log,
        operation="me",
    )
    admin_user_id = (me_data.get("me") or {}).get("id")
    if admin_user_id:
        # Check if any unrestricted group already exists
        pg_data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "query { permissionGroups(first: 10) { edges { node { id name "
                "restrictedAccessToChannels } } } }"
            ),
            allow_errors=True,
            error_log=error_log,
            operation="permissionGroups",
        )
        pg_edges = (pg_data.get("permissionGroups") or {}).get("edges") or []
        has_access = False
        for edge in pg_edges:
            node = edge.get("node") or {}
            if not node.get("restrictedAccessToChannels", True):
                has_access = True
                break
        if not has_access:
            await _gql(
                client,
                url=url,
                headers=headers,
                query=(
                    "mutation($input: PermissionGroupCreateInput!) { "
                    "permissionGroupCreate(input: $input) { group { id } "
                    "errors { field message code } } }"
                ),
                variables={
                    "input": {
                        "name": "Harness Full Access",
                        "addUsers": [admin_user_id],
                        "addChannels": [channel_id],
                        "addPermissions": [
                            "MANAGE_ORDERS", "MANAGE_PRODUCTS", "MANAGE_USERS",
                            "MANAGE_CHECKOUTS", "MANAGE_SETTINGS", "MANAGE_SHIPPING",
                            "MANAGE_DISCOUNTS", "MANAGE_GIFT_CARD", "MANAGE_TAXES",
                            "MANAGE_PAGE_TYPES_AND_ATTRIBUTES",
                            "MANAGE_PRODUCT_TYPES_AND_ATTRIBUTES",
                            "MANAGE_CHANNELS", "MANAGE_TRANSLATIONS",
                        ],
                    }
                },
                allow_errors=True,
                error_log=error_log,
                operation="permissionGroupCreate",
            )

    # Step 1: Create draft order with addresses and lines
    draft_input: dict[str, Any] = {
        "channelId": channel_id,
        "billingAddress": {
            "firstName": "John",
            "lastName": "Doe",
            "streetAddress1": "123 Test St",
            "city": "New York",
            "country": "US",
            "countryArea": "NY",
            "postalCode": "10001",
        },
        "shippingAddress": {
            "firstName": "John",
            "lastName": "Doe",
            "streetAddress1": "123 Test St",
            "city": "New York",
            "country": "US",
            "countryArea": "NY",
            "postalCode": "10001",
        },
        "lines": [
            {"variantId": variant_id, "quantity": 1},
            {"variantId": variant_id, "quantity": 2},
        ],
    }

    draft_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: DraftOrderCreateInput!) { "
            "draftOrderCreate(input: $input) { order { id } "
            "errors { field message code } } }"
        ),
        variables={"input": draft_input},
        allow_errors=True,
        error_log=error_log,
        operation="draftOrderCreate",
    )
    draft_payload = draft_data.get("draftOrderCreate")
    draft_order = (draft_payload or {}).get("order")
    if not draft_order:
        # Order creation failed (likely channel access issue) - log but don't fail the whole seed
        errors = (draft_payload or {}).get("errors") or ["no data returned"]
        error_log.append(f"Order creation skipped: {errors}")
        return False

    order_id = draft_order["id"]

    # Step 2: Add line items using orderLinesCreate (plural, Saleor 3.23.7)
    await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $input: [OrderLineCreateInput!]!) { "
            "orderLinesCreate(id: $id, input: $input) { order { id } "
            "errors { field message code } } }"
        ),
        variables={
            "id": order_id,
            "input": [
                {"variantId": variant_id, "quantity": 1},
                {"variantId": variant_id, "quantity": 2},
            ],
        },
        allow_errors=True,
        error_log=error_log,
        operation="orderLinesCreate",
    )

    fixtures["default_order_id"] = order_id
    return True


async def ensure_runtime_fixture_entities(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 60,
) -> SeedResult:
    """Create missing harness fixture entities on the target via admin mutations.

    Idempotent: reuses existing harness-reference slugs when present.
    """
    saleor_url = resolve_saleor_url_for_runner(saleor_url)
    seeded: set[str] = set()
    error_log: list[str] = []
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        fixtures = await _capture_fixtures(client, url=saleor_url, headers=headers)

        if await _ensure_channel(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.update({"default_channel_id", "default_channel"})
        if await _ensure_product_type(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.add("default_product_type_id")
        if await _ensure_reference_product(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.update(
                {
                    "default_product_id",
                    "default_slug",
                    "default_variant_id",
                    "variant_id_for_cart",
                }
            )
        seeded.update(
            await _ensure_customer_and_collection(
                client, url=saleor_url, headers=headers, fixtures=fixtures
            )
        )
        if await _ensure_category(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.add("default_category_id")
        if await _ensure_warehouse(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.add("default_warehouse_id")
        if await _ensure_order(
            client, url=saleor_url, headers=headers, fixtures=fixtures, error_log=error_log
        ):
            seeded.add("default_order_id")

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


async def _seed_storefront_fixtures(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str] | None = None,
    fixtures: dict[str, Any],
) -> dict[str, Any]:
    """Create anonymous checkout for fixture capture (reference seed workflow)."""
    channel_slug = fixtures.get("default_channel", "default-channel")
    variant_id = fixtures.get("default_variant_id")
    if variant_id and not fixtures.get("default_checkout_id"):
        anon_headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        checkout_data = await _gql(
            client,
            url=url,
            headers=anon_headers,
            query=(
                "mutation($input: CheckoutCreateInput!) { "
                "checkoutCreate(input: $input) { checkout { id token } "
                "errors { field message code } } }"
            ),
            variables={
                "input": {
                    "channel": channel_slug,
                    "lines": [{"quantity": 1, "variantId": variant_id}],
                }
            },
            allow_errors=True,
        )
        checkout = (checkout_data.get("checkoutCreate") or {}).get("checkout")
        if checkout:
            fixtures["default_checkout_id"] = checkout.get("id")
            fixtures["default_checkout_token"] = checkout.get("token")
            fixtures["variant_id_for_cart"] = variant_id
    return fixtures


async def seed_reference_data(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 60,
    dashboard_version: str | None = None,
    storefront_version: str | None = None,
) -> dict[str, Any]:
    """Ensure fixture keys exist; save to dashboard and storefront fixtures.json."""
    from app.core.config import settings

    ver = dashboard_version or settings.reference_baseline_version
    sf_ver = storefront_version or settings.reference_baseline_version

    seed_result = await ensure_runtime_fixture_entities(
        saleor_url, token, timeout=timeout
    )

    fixtures = seed_result.fixtures
    missing = [k for k in REQUIRED_FIXTURE_KEYS if not fixtures.get(k)]
    if missing:
        raise RuntimeError(
            f"Missing fixture keys after seed: {', '.join(missing)}. "
            "Ensure the target Saleor instance is reachable and supports the required mutations."
        )

    save_fixtures("dashboard", ver, fixtures)
    save_fixtures("storefront", sf_ver, fixtures)
    return fixtures
