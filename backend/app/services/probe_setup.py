"""
Mutation-first probe setup — creates required data before querying.

For each operation, defines a setup mutation that creates the entity
the probe needs, and extraction rules to capture the created entity's ID.
This eliminates the dependency on hardcoded Saleor demo data.
"""

from __future__ import annotations

import uuid
from typing import Any


def _nonce() -> str:
    return str(uuid.uuid4())[:8]


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{_nonce()}"


# ── Setup mutations per operation ────────────────────────────────────────────
# Each entry maps an L1 operation name to:
#   mutation: GraphQL mutation document ({{slug}}, {{name}}, {{uuid}} placeholders)
#   variables: variable dict with placeholders
#   extract: JSON path to the created entity's Relay ID in the response
#   category: for logging/classification
#   auth: required auth context

SETUP_MUTATIONS: dict[str, dict[str, Any]] = {
    # ── Products ─────────────────────────────────────────────────────────
    "products": {
        "mutation": """mutation($input: ProductCreateInput!) {
            productCreate(input: $input) {
                product { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Product",
                "slug": _unique_slug("setup-product"),
                "productType": "{{product_type_id}}",
            }
        },
        "extract": "$.data.productCreate.product.id",
        "category": "products",
        "auth": "staff",
    },
    "product": {
        "mutation": """mutation($input: ProductCreateInput!) {
            productCreate(input: $input) {
                product { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Product",
                "slug": _unique_slug("setup-product"),
                "productType": "{{product_type_id}}",
            }
        },
        "extract": "$.data.productCreate.product.id",
        "category": "products",
        "auth": "staff",
    },
    "productTypes": {
        "mutation": """mutation($input: ProductTypeInput!) {
            productTypeCreate(input: $input) {
                productType { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup ProductType",
                "slug": _unique_slug("setup-pt"),
                "hasVariants": True,
            }
        },
        "extract": "$.data.productTypeCreate.productType.id",
        "category": "products",
        "auth": "staff",
    },
    "productType": {
        "mutation": """mutation($input: ProductTypeInput!) {
            productTypeCreate(input: $input) {
                productType { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup ProductType",
                "slug": _unique_slug("setup-pt"),
                "hasVariants": True,
            }
        },
        "extract": "$.data.productTypeCreate.productType.id",
        "category": "products",
        "auth": "staff",
    },

    # ── Categories ───────────────────────────────────────────────────────
    "categories": {
        "mutation": """mutation($input: CategoryInput!) {
            categoryCreate(input: $input) {
                category { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Category",
                "slug": _unique_slug("setup-cat"),
            }
        },
        "extract": "$.data.categoryCreate.category.id",
        "category": "categories",
        "auth": "staff",
    },
    "category": {
        "mutation": """mutation($input: CategoryInput!) {
            categoryCreate(input: $input) {
                category { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Category",
                "slug": _unique_slug("setup-cat"),
            }
        },
        "extract": "$.data.categoryCreate.category.id",
        "category": "categories",
        "auth": "staff",
    },

    # ── Collections ──────────────────────────────────────────────────────
    "collections": {
        "mutation": """mutation($input: CollectionCreateInput!) {
            collectionCreate(input: $input) {
                collection { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Collection",
                "slug": _unique_slug("setup-coll"),
            }
        },
        "extract": "$.data.collectionCreate.collection.id",
        "category": "collections",
        "auth": "staff",
    },
    "collection": {
        "mutation": """mutation($input: CollectionCreateInput!) {
            collectionCreate(input: $input) {
                collection { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Collection",
                "slug": _unique_slug("setup-coll"),
            }
        },
        "extract": "$.data.collectionCreate.collection.id",
        "category": "collections",
        "auth": "staff",
    },

    # ── Channels ─────────────────────────────────────────────────────────
    "channels": {
        "mutation": """mutation($input: ChannelCreateInput!) {
            channelCreate(input: $input) {
                channel { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Channel",
                "slug": _unique_slug("setup-ch"),
                "currencyCode": "USD",
                "isActive": True,
            }
        },
        "extract": "$.data.channelCreate.channel.id",
        "category": "channels",
        "auth": "staff",
    },
    "channel": {
        "mutation": """mutation($input: ChannelCreateInput!) {
            channelCreate(input: $input) {
                channel { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Channel",
                "slug": _unique_slug("setup-ch"),
                "currencyCode": "USD",
                "isActive": True,
            }
        },
        "extract": "$.data.channelCreate.channel.id",
        "category": "channels",
        "auth": "staff",
    },

    # ── Attributes ───────────────────────────────────────────────────────
    "attributes": {
        "mutation": """mutation($input: AttributeCreateInput!) {
            attributeCreate(input: $input) {
                attribute { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Attribute",
                "slug": _unique_slug("setup-attr"),
                "inputType": "DROPDOWN",
                "type": "PRODUCT_TYPE",
            }
        },
        "extract": "$.data.attributeCreate.attribute.id",
        "category": "attributes",
        "auth": "staff",
    },
    "attribute": {
        "mutation": """mutation($input: AttributeCreateInput!) {
            attributeCreate(input: $input) {
                attribute { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Attribute",
                "slug": _unique_slug("setup-attr"),
                "inputType": "DROPDOWN",
                "type": "PRODUCT_TYPE",
            }
        },
        "extract": "$.data.attributeCreate.attribute.id",
        "category": "attributes",
        "auth": "staff",
    },

    # ── Pages ────────────────────────────────────────────────────────────
    "pages": {
        "mutation": """mutation($input: PageCreateInput!) {
            pageCreate(input: $input) {
                page { id title slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "title": "Setup Page",
                "slug": _unique_slug("setup-page"),
                "content": '{"blocks": [{"data": {"text": "Setup"}, "type": "paragraph"}]}',
            }
        },
        "extract": "$.data.pageCreate.page.id",
        "category": "pages",
        "auth": "staff",
    },
    "page": {
        "mutation": """mutation($input: PageCreateInput!) {
            pageCreate(input: $input) {
                page { id title slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "title": "Setup Page",
                "slug": _unique_slug("setup-page"),
                "content": '{"blocks": [{"data": {"text": "Setup"}, "type": "paragraph"}]}',
            }
        },
        "extract": "$.data.pageCreate.page.id",
        "category": "pages",
        "auth": "staff",
    },

    # ── Shipping Zones ───────────────────────────────────────────────────
    "shippingZones": {
        "mutation": """mutation($input: ShippingZoneCreateInput!) {
            shippingZoneCreate(input: $input) {
                shippingZone { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Shipping Zone",
                "countries": ["US"],
            }
        },
        "extract": "$.data.shippingZoneCreate.shippingZone.id",
        "category": "shipping",
        "auth": "staff",
    },
    "shippingZone": {
        "mutation": """mutation($input: ShippingZoneCreateInput!) {
            shippingZoneCreate(input: $input) {
                shippingZone { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Shipping Zone",
                "countries": ["US"],
            }
        },
        "extract": "$.data.shippingZoneCreate.shippingZone.id",
        "category": "shipping",
        "auth": "staff",
    },

    # ── Warehouses ───────────────────────────────────────────────────────
    "warehouses": {
        "mutation": """mutation($input: WarehouseCreateInput!) {
            createWarehouse(input: $input) {
                warehouse { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Warehouse",
                "slug": _unique_slug("setup-wh"),
                "address": {
                    "streetAddress1": "123 Test St",
                    "city": "Testville",
                    "country": "US",
                    "postalCode": "12345",
                },
            }
        },
        "extract": "$.data.createWarehouse.warehouse.id",
        "category": "warehouses",
        "auth": "staff",
    },
    "warehouse": {
        "mutation": """mutation($input: WarehouseCreateInput!) {
            createWarehouse(input: $input) {
                warehouse { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Warehouse",
                "slug": _unique_slug("setup-wh"),
                "address": {
                    "streetAddress1": "123 Test St",
                    "city": "Testville",
                    "country": "US",
                    "postalCode": "12345",
                },
            }
        },
        "extract": "$.data.createWarehouse.warehouse.id",
        "category": "warehouses",
        "auth": "staff",
    },

    # ── Staff ────────────────────────────────────────────────────────────
    "staffUsers": {
        "mutation": """mutation($input: StaffCreateInput!) {
            staffCreate(input: $input) {
                user { id email }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "email": f"setup-staff-{_nonce()}@example.com",
                "firstName": "Setup",
                "lastName": "Staff",
                "password": "testpass123!",
            }
        },
        "extract": "$.data.staffCreate.user.id",
        "category": "staff",
        "auth": "staff",
    },

    # ── Customers ────────────────────────────────────────────────────────
    "customers": {
        "mutation": """mutation($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user { id email }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "email": f"setup-customer-{_nonce()}@example.com",
                "firstName": "Setup",
                "lastName": "Customer",
                "password": "testpass123!",
            }
        },
        "extract": "$.data.customerCreate.user.id",
        "category": "customers",
        "auth": "staff",
    },
    "customer": {
        "mutation": """mutation($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user { id email }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "email": f"setup-customer-{_nonce()}@example.com",
                "firstName": "Setup",
                "lastName": "Customer",
                "password": "testpass123!",
            }
        },
        "extract": "$.data.customerCreate.user.id",
        "category": "customers",
        "auth": "staff",
    },

    # ── Gift Cards ───────────────────────────────────────────────────────
    "giftCards": {
        "mutation": """mutation($input: GiftCardCreateInput!) {
            giftCardCreate(input: $input) {
                giftCard { id code }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "balance": {"amount": 10.0, "currency": "USD"},
                "isActive": True,
            }
        },
        "extract": "$.data.giftCardCreate.giftCard.id",
        "category": "giftcards",
        "auth": "staff",
    },
    "giftCard": {
        "mutation": """mutation($input: GiftCardCreateInput!) {
            giftCardCreate(input: $input) {
                giftCard { id code }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "balance": {"amount": 10.0, "currency": "USD"},
                "isActive": True,
            }
        },
        "extract": "$.data.giftCardCreate.giftCard.id",
        "category": "giftcards",
        "auth": "staff",
    },

    # ── Menus ────────────────────────────────────────────────────────────
    "menus": {
        "mutation": """mutation($input: MenuCreateInput!) {
            menuCreate(input: $input) {
                menu { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Menu",
                "slug": _unique_slug("setup-menu"),
            }
        },
        "extract": "$.data.menuCreate.menu.id",
        "category": "menus",
        "auth": "staff",
    },
    "menu": {
        "mutation": """mutation($input: MenuCreateInput!) {
            menuCreate(input: $input) {
                menu { id name slug }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": "Setup Menu",
                "slug": _unique_slug("setup-menu"),
            }
        },
        "extract": "$.data.menuCreate.menu.id",
        "category": "menus",
        "auth": "staff",
    },

    # ── Vouchers ─────────────────────────────────────────────────────────
    "vouchers": {
        "mutation": """mutation($input: VoucherInput!) {
            voucherCreate(input: $input) {
                voucher { id code }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "type": "ENTIRE_ORDER",
                "code": _unique_slug("voucher"),
                "discountValueType": "PERCENTAGE",
                "discountValue": 10,
            }
        },
        "extract": "$.data.voucherCreate.voucher.id",
        "category": "vouchers",
        "auth": "staff",
    },
    "voucher": {
        "mutation": """mutation($input: VoucherInput!) {
            voucherCreate(input: $input) {
                voucher { id code }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "type": "ENTIRE_ORDER",
                "code": _unique_slug("voucher"),
                "discountValueType": "PERCENTAGE",
                "discountValue": 10,
            }
        },
        "extract": "$.data.voucherCreate.voucher.id",
        "category": "vouchers",
        "auth": "staff",
    },

    # ── Draft Orders ─────────────────────────────────────────────────────
    "draftOrders": {
        "mutation": """mutation {
            draftOrderCreate(input: {}) {
                order { id status }
                errors { field message }
            }
        }""",
        "variables": lambda: {},
        "extract": "$.data.draftOrderCreate.order.id",
        "category": "orders",
        "auth": "staff",
    },

    # ── Orders ───────────────────────────────────────────────────────────
    "orders": {
        "mutation": """mutation {
            draftOrderCreate(input: {}) {
                order { id status }
                errors { field message }
            }
        }""",
        "variables": lambda: {},
        "extract": "$.data.draftOrderCreate.order.id",
        "category": "orders",
        "auth": "staff",
    },

    # ── Users ────────────────────────────────────────────────────────────
    "users": {
        "mutation": """mutation($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user { id email }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "email": f"setup-user-{_nonce()}@example.com",
                "firstName": "Setup",
                "lastName": "User",
                "password": "testpass123!",
            }
        },
        "extract": "$.data.customerCreate.user.id",
        "category": "account",
        "auth": "staff",
    },
    "user": {
        "mutation": """mutation($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user { id email }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "email": f"setup-user-{_nonce()}@example.com",
                "firstName": "Setup",
                "lastName": "User",
                "password": "testpass123!",
            }
        },
        "extract": "$.data.customerCreate.user.id",
        "category": "account",
        "auth": "staff",
    },

    # ── Permission Groups ────────────────────────────────────────────────
    "permissionGroups": {
        "mutation": """mutation($input: PermissionGroupCreateInput!) {
            permissionGroupCreate(input: $input) {
                group { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": f"Setup Group {_nonce()}",
            }
        },
        "extract": "$.data.permissionGroupCreate.group.id",
        "category": "account",
        "auth": "staff",
    },

    # ── Webhooks ─────────────────────────────────────────────────────────
    "webhooks": {
        "mutation": """mutation($input: WebhookCreateInput!) {
            webhookCreate(input: $input) {
                webhook { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": f"Setup Webhook {_nonce()}",
                "targetUrl": "https://example.com/hook",
                "events": ["ORDER_CREATED"],
                "isActive": False,
            }
        },
        "extract": "$.data.webhookCreate.webhook.id",
        "category": "webhooks",
        "auth": "staff",
    },

    # ── Shop ─────────────────────────────────────────────────────────────
    "shop": {
        "mutation": None,  # Shop is read-only; use existing data
        "variables": lambda: {},
        "extract": None,
        "category": "shop",
        "auth": "staff",
    },

    # ── Tax Classes ──────────────────────────────────────────────────────
    "taxClasses": {
        "mutation": """mutation($input: TaxClassCreateInput!) {
            taxClassCreate(input: $input) {
                taxClass { id name }
                errors { field message }
            }
        }""",
        "variables": lambda: {
            "input": {
                "name": f"Setup Tax Class {_nonce()}",
            }
        },
        "extract": "$.data.taxClassCreate.taxClass.id",
        "category": "tax",
        "auth": "staff",
    },
}


def get_setup_for_operation(operation_name: str) -> dict[str, Any] | None:
    """Return the setup mutation config for an operation, or None if no setup needed."""
    return SETUP_MUTATIONS.get(operation_name)


def needs_setup(operation_name: str, golden_contract: str | None) -> bool:
    """Determine if an operation needs data setup before querying.

    Returns True if:
    - The operation has a registered setup mutation
    - The golden contract is 'success' (error probes don't need data)
    - The operation is not a read-only shop query with no setup
    """
    if golden_contract and golden_contract != "success":
        return False
    setup = SETUP_MUTATIONS.get(operation_name)
    if setup is None:
        return False
    return setup.get("mutation") is not None
