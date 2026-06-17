"""
Legacy Saleor demo topology mutation helpers.

Retained for unit tests of individual seed steps. Certification runs use
mutation-first harness topology in reference_seed.py instead.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.reference_seed import (
    _append_mutation_errors,
    _capture_fixtures,
    _gql,
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
    "Default for click and collect",
)

DEMO_CHANNEL_WAREHOUSES: dict[str, tuple[str, ...]] = {
    DEMO_CHANNEL_USD_SLUG: DEMO_WAREHOUSE_NAMES,
    DEMO_CHANNEL_PLN_SLUG: (
        "Default",
        "Europe",
        "Oceania",
        "Asia",
        "Americas",
        "Africa",
    ),
}

# Minimal shipping zones for channeldiagnostics golden (name → country codes).
DEMO_SHIPPING_ZONE_SPECS: tuple[tuple[str, list[str], tuple[str, ...]], ...] = (
    ("Default", ["US"], ("Default Warehouse", "Default", "Default for click and collect")),
    ("Europe", ["DE", "FR", "PL"], ("Europe",)),
    ("Oceania", ["AU", "NZ"], ("Oceania",)),
    ("Asia", ["JP", "CN"], ("Asia",)),
    ("Americas", ["BR", "CA"], ("Americas",)),
    ("Africa", ["ZA", "NG"], ("Africa",)),
)

DEMO_CATEGORY_SPECS: tuple[tuple[str, str, str | None], ...] = (
    ("Default Category", "default-category", None),
    ("Accessories", "accessories", None),
    ("Audiobooks", "audiobooks", "accessories"),
    ("Apparel", "apparel", None),
    ("Sneakers", "sneakers", "apparel"),
    ("Sweatshirts", "sweatshirts", "apparel"),
    ("Groceries", "groceries", None),
    ("Juices", "juices", None),
)

DEMO_COLLECTION_SPECS: tuple[tuple[str, str], ...] = (
    ("Featured Products", "featured-products"),
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
    ("harness-storefront-customer@example.com", "", ""),
    ("jade.guerrero@example.com", "Jade", "Guerrero"),
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
    pln = await _channel_by_slug(client, url=url, headers=headers, slug=DEMO_CHANNEL_PLN_SLUG)
    if pln:
        fixtures["storefront_channel_id"] = pln["id"]
        fixtures["storefront_channel"] = pln.get("slug") or DEMO_CHANNEL_PLN_SLUG
        seeded.update({"storefront_channel_id", "storefront_channel"})
    return seeded


def _demo_channel_ids(fixtures: dict[str, Any]) -> list[str]:
    """USD + PLN channel IDs for multi-channel catalog publishing."""
    ids: list[str] = []
    for key in ("default_channel_id", "storefront_channel_id"):
        cid = fixtures.get(key)
        if cid and cid not in ids:
            ids.append(cid)
    return ids


async def _ensure_product_channel_listings(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    product_id: str,
    channel_ids: list[str],
    error_log: list[str],
) -> set[str]:
    seeded: set[str] = set()
    if not channel_ids:
        return seeded
    data = await _gql(
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
            "input": {
                "updateChannels": [
                    {"channelId": cid, "isPublished": True} for cid in channel_ids
                ],
            },
        },
        allow_errors=True,
        error_log=error_log,
        operation="productChannelListingUpdate(multi)",
    )
    if not (data.get("productChannelListingUpdate") or {}).get("errors"):
        seeded.add("product_channel_listings")
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
                "createWarehouse(input: $input) { warehouse { id name } "
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
            operation="createWarehouse",
        )
        payload = data.get("createWarehouse")
        if (payload or {}).get("warehouse"):
            seeded.add(f"warehouse:{name}")
        else:
            _append_mutation_errors(error_log, f"createWarehouse({name})", payload)

    default_wh = await _warehouse_by_name(
        client, url=url, headers=headers, name="Default Warehouse"
    )
    if default_wh:
        fixtures["default_warehouse_id"] = default_wh["id"]
        seeded.add("default_warehouse_id")
    return seeded


async def _warehouses_by_name(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
) -> dict[str, str]:
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { warehouses(first: 50) { edges { node { id name } } } }",
        allow_errors=True,
    )
    out: dict[str, str] = {}
    for edge in (data.get("warehouses") or {}).get("edges") or []:
        node = edge.get("node") or {}
        name = node.get("name")
        if name and node.get("id"):
            out[str(name)] = str(node["id"])
    return out


async def assign_demo_channel_warehouses(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Assign demo warehouses to channels (matches channels golden topology)."""
    seeded: set[str] = set()
    warehouse_ids = await _warehouses_by_name(client, url=url, headers=headers)
    for slug, warehouse_names in DEMO_CHANNEL_WAREHOUSES.items():
        channel = await _channel_by_slug(client, url=url, headers=headers, slug=slug)
        if not channel:
            continue
        add_ids = [warehouse_ids[n] for n in warehouse_names if n in warehouse_ids]
        if not add_ids:
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $input: ChannelUpdateInput!) { "
                "channelUpdate(id: $id, input: $input) { channel { id slug } "
                "errors { field message code } } }"
            ),
            variables={"id": channel["id"], "input": {"addWarehouses": add_ids}},
            allow_errors=True,
            error_log=error_log,
            operation=f"channelUpdate({slug})",
        )
        payload = data.get("channelUpdate")
        if (payload or {}).get("channel"):
            seeded.add(f"channel_warehouses:{slug}")
        else:
            _append_mutation_errors(error_log, f"channelUpdate({slug})", payload)
    return seeded


async def seed_demo_site_settings(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    error_log: list[str],
) -> set[str]:
    """Enable legacy shipping-zone stock availability (sitesettings / channeldiagnostics goldens)."""
    seeded: set[str] = set()
    shop = await _gql(
        client,
        url=url,
        headers=headers,
        query="query { shop { useLegacyShippingZoneStockAvailability } }",
        allow_errors=True,
    )
    if (shop.get("shop") or {}).get("useLegacyShippingZoneStockAvailability") is True:
        return seeded
    data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: ShopSettingsInput!) { "
            "shopSettingsUpdate(input: $input) { shop { useLegacyShippingZoneStockAvailability } "
            "errors { field message code } } }"
        ),
        variables={"input": {"useLegacyShippingZoneStockAvailability": True}},
        allow_errors=True,
        error_log=error_log,
        operation="shopSettingsUpdate",
    )
    payload = data.get("shopSettingsUpdate")
    shop_out = (payload or {}).get("shop")
    if shop_out and shop_out.get("useLegacyShippingZoneStockAvailability") is True:
        seeded.add("site_settings:legacy_shipping")
    else:
        _append_mutation_errors(error_log, "shopSettingsUpdate", payload)
    return seeded


async def _shipping_zone_by_name(
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
        query="query { shippingZones(first: 50) { edges { node { id name } } } }",
        allow_errors=True,
    )
    for edge in (data.get("shippingZones") or {}).get("edges") or []:
        node = edge.get("node") or {}
        if node.get("name") == name:
            return node
    return None


async def seed_demo_shipping_zones(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create named shipping zones with warehouses (channeldiagnostics golden)."""
    seeded: set[str] = set()
    warehouse_ids = await _warehouses_by_name(client, url=url, headers=headers)
    usd = await _channel_by_slug(
        client, url=url, headers=headers, slug=DEMO_CHANNEL_USD_SLUG
    )
    usd_channel_id = (usd or {}).get("id")
    zone_ids: list[str] = []

    for zone_name, countries, warehouse_names in DEMO_SHIPPING_ZONE_SPECS:
        existing = await _shipping_zone_by_name(
            client, url=url, headers=headers, name=zone_name
        )
        if existing:
            zone_ids.append(existing["id"])
            continue
        wh_ids = [warehouse_ids[n] for n in warehouse_names if n in warehouse_ids]
        zone_input: dict[str, Any] = {
            "name": zone_name,
            "countries": countries,
            "default": zone_name == "Default",
        }
        if wh_ids:
            zone_input["addWarehouses"] = wh_ids
        if usd_channel_id:
            zone_input["addChannels"] = [usd_channel_id]
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: ShippingZoneCreateInput!) { "
                "shippingZoneCreate(input: $input) { shippingZone { id name } "
                "errors { field message code } } }"
            ),
            variables={"input": zone_input},
            allow_errors=True,
            error_log=error_log,
            operation=f"shippingZoneCreate({zone_name})",
        )
        payload = data.get("shippingZoneCreate")
        zone = (payload or {}).get("shippingZone")
        if zone:
            seeded.add(f"shipping_zone:{zone_name}")
            zone_ids.append(zone["id"])
        else:
            _append_mutation_errors(error_log, f"shippingZoneCreate({zone_name})", payload)

    pln = await _channel_by_slug(
        client, url=url, headers=headers, slug=DEMO_CHANNEL_PLN_SLUG
    )
    pln_channel_id = (pln or {}).get("id")
    if pln_channel_id and zone_ids:
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $input: ChannelUpdateInput!) { "
                "channelUpdate(id: $id, input: $input) { channel { id } "
                "errors { field message code } } }"
            ),
            variables={"id": pln_channel_id, "input": {"addShippingZones": zone_ids}},
            allow_errors=True,
            error_log=error_log,
            operation="channelUpdate(pln-shipping-zones)",
        )
        if (data.get("channelUpdate") or {}).get("channel"):
            seeded.add("channel_shipping_zones:channel-pln")
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
                "mutation($input: UserCreateInput!) { "
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
    channel_ids = _demo_channel_ids(fixtures)
    product_type_id = fixtures.get("default_product_type_id")
    if not channel_ids or not product_type_id:
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
                    "channelListings": [
                        {"channelId": cid, "isPublished": True} for cid in channel_ids
                    ],
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


# ── Extended fixture coverage (pages, attributes, vouchers, menus) ───────────

async def seed_demo_pages(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create pages with page types for L3 bundle coverage."""
    seeded: set[str] = set()
    page_specs = [
        ("About", "about"),
        ("CozyNest", "cozynest"),
        ("Damaged Item", "damaged-item"),
        ("Frutello", "frutello"),
        ("Incorrect Address", "incorrect-address"),
        ("Package Lost", "package-lost"),
        ("Package Not Picked Up By Customer", "package-not-picked-up-by-customer"),
        ("Saleor Loom", "saleor-loom"),
    ]

    # Ensure page type exists
    pt_result = await _gql(
        client,
        url=url,
        headers=headers,
        query="""mutation($input: PageTypeCreateInput!) {
            pageTypeCreate(input: $input) { pageType { id name } errors { field message } }
        }""",
        variables={"input": {"name": "Default Page Type"}},
        allow_errors=True,
        error_log=error_log,
        operation="pageTypeCreate",
    )
    pt_data = (pt_result.get("pageTypeCreate") or {})
    pt_errors = pt_data.get("errors") or []
    pt = pt_data.get("pageType")

    # If creation failed because it already exists, try to find it
    if not pt and pt_errors:
        find_result = await _gql(
            client,
            url=url,
            headers=headers,
            query="{ pageTypes(first: 1) { edges { node { id name } } } }",
        )
        edges = (find_result.get("pageTypes") or {}).get("edges") or []
        if edges:
            pt = edges[0].get("node")

    if not pt:
        return seeded

    page_type_id = pt["id"]
    for title, slug in page_specs:
        result = await _gql(
            client,
            url=url,
            headers=headers,
            query="""mutation($input: PageCreateInput!) {
                pageCreate(input: $input) { page { id title slug } errors { field message } }
            }""",
            variables={
                "input": {
                    "title": title,
                    "slug": slug,
                    "pageType": page_type_id,
                    "isPublished": True,
                    "content": '{"blocks": [{"data": {"text": "%s"}, "type": "paragraph"}]}' % title,
                }
            },
            allow_errors=True,
            error_log=error_log,
            operation="pageCreate",
        )
        page_data = (result.get("pageCreate") or {})
        page = page_data.get("page")
        if page:
            seeded.add(f"page_{slug}")
    return seeded


async def seed_demo_attributes(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create attributes and attribute values for L3 bundle coverage."""
    seeded: set[str] = set()

    # Create a product attribute
    result = await _gql(
        client,
        url=url,
        headers=headers,
        query="""mutation($input: AttributeCreateInput!) {
            attributeCreate(input: $input) { attribute { id name slug } errors { field message } }
        }""",
        variables={
            "input": {
                "name": "Brand",
                "slug": "brand",
                "inputType": "DROPDOWN",
                "type": "PRODUCT_TYPE",
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="attributeCreate",
    )
    attr_data = (result.get("attributeCreate") or {})
    attr = attr_data.get("attribute")
    if not attr:
        # Try to find existing
        find = await _gql(
            client, url=url, headers=headers,
            query="""{ attributes(first: 1, filter: {type: PRODUCT_TYPE}) {
                edges { node { id name slug } } } }""",
        )
        edges = (find.get("attributes") or {}).get("edges") or []
        if edges:
            attr = edges[0].get("node")

    if attr:
        seeded.add("attribute_brand")
        # Create attribute values
        for val_name in ("Digital Audio", "Saleor Publishing"):
            await _gql(
                client,
                url=url,
                headers=headers,
                query="""mutation($input: AttributeValueCreateInput!) {
                    attributeValueCreate(input: $input) { attributeValue { id name } errors { field message } }
                }""",
                variables={
                    "input": {
                        "attribute": attr["id"],
                        "name": val_name,
                    }
                },
                allow_errors=True,
                error_log=error_log,
                operation="attributeValueCreate",
            )

    return seeded


async def seed_demo_vouchers(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create vouchers for L3 bundle coverage."""
    seeded: set[str] = set()
    result = await _gql(
        client,
        url=url,
        headers=headers,
        query="""mutation($input: VoucherInput!) {
            voucherCreate(input: $input) { voucher { id code } errors { field message } }
        }""",
        variables={
            "input": {
                "type": "ENTIRE_ORDER",
                "code": "DEMO-VOUCHER-10",
                "discountValueType": "PERCENTAGE",
                "discountValue": 10,
                "isActive": True,
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="voucherCreate",
    )
    voucher_data = (result.get("voucherCreate") or {})
    if voucher_data.get("voucher"):
        seeded.add("voucher_demo")
    return seeded


async def seed_demo_gift_cards(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create gift cards for L3 bundle coverage."""
    seeded: set[str] = set()
    for amount in (10, 50, 500):
        result = await _gql(
            client,
            url=url,
            headers=headers,
            query="""mutation {
                giftCardCreate(input: { balance: { amount: %d.0, currency: "USD" } }) {
                    giftCard { id code } errors { field message }
                }
            }""" % amount,
            allow_errors=True,
            error_log=error_log,
            operation="giftCardCreate",
        )
        gc_data = (result.get("giftCardCreate") or {})
        if gc_data.get("giftCard"):
            seeded.add(f"gift_card_{amount}")
    return seeded


async def seed_demo_menus(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create menus for L3 bundle coverage."""
    seeded: set[str] = set()
    result = await _gql(
        client,
        url=url,
        headers=headers,
        query="""mutation($input: MenuCreateInput!) {
            menuCreate(input: $input) { menu { id name slug } errors { field message } }
        }""",
        variables={"input": {"name": "Sidebar Menu", "slug": "sidebar-menu"}},
        allow_errors=True,
        error_log=error_log,
        operation="menuCreate",
    )
    menu_data = (result.get("menuCreate") or {})
    if menu_data.get("menu"):
        seeded.add("menu_sidebar")
    return seeded



async def _category_by_slug(
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
        query=(
            "query($slug: String!) { category(slug: $slug) { id name slug } }"
        ),
        variables={"slug": slug},
        allow_errors=True,
    )
    return data.get("category")


async def seed_demo_categories(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create demo category tree for search/homepage probes."""
    seeded: set[str] = set()
    slug_to_id: dict[str, str] = {}

    for name, slug, parent_slug in DEMO_CATEGORY_SPECS:
        existing = await _category_by_slug(
            client, url=url, headers=headers, slug=slug
        )
        if existing:
            slug_to_id[slug] = existing["id"]
            if slug == "default-category" and not fixtures.get("default_category_id"):
                fixtures["default_category_id"] = existing["id"]
            continue
        parent_id = slug_to_id.get(parent_slug) if parent_slug else None
        cat_input: dict[str, Any] = {"name": name, "slug": slug}
        if parent_id:
            cat_input["parent"] = parent_id
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: CategoryInput!) { "
                "categoryCreate(input: $input) { category { id slug } "
                "errors { field message code } } }"
            ),
            variables={"input": cat_input},
            allow_errors=True,
            error_log=error_log,
            operation=f"categoryCreate({slug})",
        )
        payload = data.get("categoryCreate")
        category = (payload or {}).get("category")
        if category:
            slug_to_id[slug] = category["id"]
            seeded.add(f"category:{slug}")
            if slug == "default-category":
                fixtures["default_category_id"] = category["id"]
        else:
            _append_mutation_errors(error_log, f"categoryCreate({slug})", payload)
    return seeded


async def _collection_by_slug(
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
            "collection(slug: $slug, channel: $ch) { id name slug } }"
        ),
        variables={"slug": slug, "ch": channel},
        allow_errors=True,
    )
    return data.get("collection")


async def seed_demo_collections(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Create demo collections and publish on USD + PLN channels."""
    seeded: set[str] = set()
    channel_slug = fixtures.get("default_channel") or DEMO_CHANNEL_USD_SLUG
    channel_ids = _demo_channel_ids(fixtures)
    if not channel_ids:
        return seeded

    for name, slug in DEMO_COLLECTION_SPECS:
        existing = await _collection_by_slug(
            client, url=url, headers=headers, slug=slug, channel=channel_slug
        )
        if existing:
            if not fixtures.get("default_collection_id"):
                fixtures["default_collection_id"] = existing["id"]
            listing = await _gql(
                client,
                url=url,
                headers=headers,
                query=(
                    "mutation($id: ID!, $input: CollectionChannelListingUpdateInput!) { "
                    "collectionChannelListingUpdate(id: $id, input: $input) { "
                    "errors { field message code } } }"
                ),
                variables={
                    "id": existing["id"],
                    "input": {
                        "addChannels": [
                            {"channelId": cid, "isPublished": True} for cid in channel_ids
                        ],
                    },
                },
                allow_errors=True,
                error_log=error_log,
                operation=f"collectionChannelListingUpdate({slug})",
            )
            if not (listing.get("collectionChannelListingUpdate") or {}).get("errors"):
                seeded.add(f"collection_published:{slug}")
            continue
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($input: CollectionCreateInput!) { "
                "collectionCreate(input: $input) { collection { id slug } "
                "errors { field message code } } }"
            ),
            variables={"input": {"name": name, "slug": slug}},
            allow_errors=True,
            error_log=error_log,
            operation=f"collectionCreate({slug})",
        )
        payload = data.get("collectionCreate")
        collection = (payload or {}).get("collection")
        if not collection:
            _append_mutation_errors(error_log, f"collectionCreate({slug})", payload)
            continue
        seeded.add(f"collection:{slug}")
        fixtures["default_collection_id"] = collection["id"]
        listing = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $input: CollectionChannelListingUpdateInput!) { "
                "collectionChannelListingUpdate(id: $id, input: $input) { "
                "errors { field message code } } }"
            ),
            variables={
                "id": collection["id"],
                "input": {
                    "addChannels": [
                        {"channelId": cid, "isPublished": True} for cid in channel_ids
                    ],
                },
            },
            allow_errors=True,
            error_log=error_log,
            operation=f"collectionChannelListingUpdate({slug})",
        )
        if not (listing.get("collectionChannelListingUpdate") or {}).get("errors"):
            seeded.add(f"collection_published:{slug}")
    return seeded


async def assign_demo_catalog_products(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    fixtures: dict[str, Any],
    error_log: list[str],
) -> set[str]:
    """Assign demo product to categories and featured collection."""
    seeded: set[str] = set()
    product_id = fixtures.get("default_product_id")
    if not product_id:
        return seeded

    juices = await _category_by_slug(
        client, url=url, headers=headers, slug="juices"
    )
    if juices:
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($product: ID!, $category: ID!) { "
                "productUpdate(id: $product, input: {category: $category}) { "
                "product { id } errors { field message code } } }"
            ),
            variables={"product": product_id, "category": juices["id"]},
            allow_errors=True,
            error_log=error_log,
            operation="productUpdate(category)",
        )
        if (data.get("productUpdate") or {}).get("product"):
            seeded.add("product_category:juices")

    collection_id = fixtures.get("default_collection_id")
    if collection_id:
        data = await _gql(
            client,
            url=url,
            headers=headers,
            query=(
                "mutation($id: ID!, $products: [ID!]!) { "
                "collectionAddProducts(collectionId: $id, products: $products) { "
                "collection { id } errors { field message code } } }"
            ),
            variables={"id": collection_id, "products": [product_id]},
            allow_errors=True,
            error_log=error_log,
            operation="collectionAddProducts",
        )
        if (data.get("collectionAddProducts") or {}).get("collection"):
            seeded.add("collection_product:apple-juice")
    return seeded
