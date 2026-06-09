"""
Seed minimal reference data on official Saleor for L3 fixture capture.

Uses populatedb/demo data when present; creates harness-reference entities only for
missing fixture keys required by L3 dashboard bundles.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.services.client_bundles import save_fixtures

REFERENCE_PRODUCT_SLUG = "harness-reference-product"
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


async def _gql(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    query: str,
    variables: dict[str, Any] | None = None,
    allow_errors: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = await client.post(url, json=payload, headers=headers)
    body = resp.json()
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


async def seed_reference_data(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 60,
    dashboard_version: str | None = None,
) -> dict[str, Any]:
    """Ensure fixture keys exist; save to dashboard fixtures.json."""
    from app.core.config import settings

    ver = dashboard_version or settings.reference_baseline_version
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        fixtures = await _capture_fixtures(client, url=saleor_url, headers=headers)

        channel_id = fixtures.get("default_channel_id")
        channel_slug = fixtures.get("default_channel")
        if not channel_id:
            raise RuntimeError("No channel found — run Saleor migrate + populatedb first")

        if not fixtures.get("default_customer_id"):
            create_cust = await _gql(
                client,
                url=saleor_url,
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

        if not fixtures.get("default_collection_id"):
            create_coll = await _gql(
                client,
                url=saleor_url,
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

        missing = [k for k in REQUIRED_FIXTURE_KEYS if not fixtures.get(k)]
        if missing:
            raise RuntimeError(
                f"Missing fixture keys after seed: {', '.join(missing)}. "
                "Run `just fresh` (includes populatedb) before recording L3 bundles."
            )

        if fixtures.get("default_collection_id") and fixtures.get("default_product_id"):
            await _gql(
                client,
                url=saleor_url,
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

        fixtures = await _capture_fixtures(client, url=saleor_url, headers=headers)
        still_missing = [k for k in REQUIRED_FIXTURE_KEYS if not fixtures.get(k)]
        if still_missing:
            raise RuntimeError(f"Missing fixture keys: {', '.join(still_missing)}")

    save_fixtures("dashboard", ver, fixtures)
    return fixtures
