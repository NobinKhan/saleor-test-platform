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
    "default_order_id",
    "default_collection_id",
)

STOREFRONT_FIXTURE_KEYS = (
    "default_checkout_id",
    "default_checkout_token",
    "variant_id_for_cart",
)


STOREFRONT_FIXTURE_KEYS = (
    "default_checkout_id",
    "default_checkout_token",
    "variant_id_for_cart",
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
    fixtures: dict[str, Any] = {
        "default_channel": "default-channel",
        "default_slug": "test-product",
        "placeholder_id": "00000000-0000-0000-0000-000000000000",
    }

    ch_data = await _gql(
        client, url=url, headers=headers, query="query { channels { id slug } }"
    )
    channels = ch_data.get("channels") or []
    if channels:
        fixtures["default_channel"] = channels[0].get("slug") or fixtures["default_channel"]
        fixtures["default_channel_id"] = channels[0].get("id")

    ch = fixtures["default_channel"]
    prod_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($ch: String!) { products(first: 1, channel: $ch) "
            "{ edges { node { id slug variants { id } } } } }"
        ),
        variables={"ch": ch},
        allow_errors=True,
    )
    edges = (prod_data.get("products") or {}).get("edges") or []
    if edges:
        node = edges[0].get("node") or {}
        fixtures["default_slug"] = node.get("slug") or fixtures["default_slug"]
        fixtures["default_product_id"] = node.get("id")
        variants = node.get("variants") or []
        if variants:
            fixtures["default_variant_id"] = variants[0].get("id")

    pt_data = await _gql(
        client, url=url, headers=headers, query="query { productTypes(first: 1) { edges { node { id } } } }", allow_errors=True
    )
    pt_edges = (pt_data.get("productTypes") or {}).get("edges") or []
    if pt_edges:
        fixtures["default_product_type_id"] = pt_edges[0]["node"]["id"]

    for query_name, key in (
        ("orders(first: 1)", "default_order_id"),
        ("customers(first: 1)", "default_customer_id"),
        ("warehouses(first: 1)", "default_warehouse_id"),
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

    coll_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "query($ch: String!) { collections(first: 1, channel: $ch) "
            "{ edges { node { id } } } }"
        ),
        variables={"ch": ch},
        allow_errors=True,
    )
    coll_edges = (coll_data.get("collections") or {}).get("edges") or []
    if coll_edges:
        fixtures["default_collection_id"] = coll_edges[0]["node"]["id"]

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
            "query($slug: String!, $channel: String!) { "
            "product(slug: $slug, channel: $channel) { id slug variants { id } } }"
        ),
        variables={"slug": REFERENCE_PRODUCT_SLUG, "channel": channel_slug or "default-channel"},
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
            fixtures["default_variant_id"] = variants[0]["id"]
            fixtures["variant_id_for_cart"] = variants[0]["id"]
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
                "channelListings": [{"channelId": channel_id, "isPublished": True}],
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
    variants = product.get("variants") or []
    if variants:
        fixtures["default_variant_id"] = variants[0]["id"]
        fixtures["variant_id_for_cart"] = variants[0]["id"]
        return True

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
                "channelListings": [{"channelId": channel_id, "price": "10.00"}],
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="productVariantCreate",
    )
    variant_payload = variant_data.get("productVariantCreate")
    variant = (variant_payload or {}).get("productVariant")
    if variant:
        fixtures["default_variant_id"] = variant["id"]
        fixtures["variant_id_for_cart"] = variant["id"]
        return True
    _append_mutation_errors(error_log, "productVariantCreate", variant_payload)
    return False


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
            seeded.add("default_customer_id")

    if channel_id and not fixtures.get("default_collection_id"):
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
                    "channelListings": [{"channelId": channel_id, "isPublished": True}],
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


async def _seed_storefront_fixtures(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
) -> dict[str, Any]:
    channel_slug = fixtures.get("default_channel", "default-channel")
    variant_id = fixtures.get("default_variant_id")
    if variant_id and not fixtures.get("default_checkout_id"):
        checkout_data = await _gql(
            client,
            url=url,
            headers=headers,
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
            "Run `just fresh` (includes populatedb) before recording L3 bundles."
        )

    save_fixtures("dashboard", ver, fixtures)
    save_fixtures("storefront", sf_ver, fixtures)
    return fixtures
