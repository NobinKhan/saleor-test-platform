"""
Embedded Saleor SDK checkout/account GraphQL documents for storefront L3 import.

The legacy storefront vendor inlines catalog queries only; checkout mutations live
in @saleor/sdk. These documents are vendored here for stable bundle import.
"""

from __future__ import annotations

from typing import Any

SDK_STOREFRONT_DOCUMENTS: list[dict[str, Any]] = [
    {
        "operation_name": "CheckoutCreate",
        "document": (
            "mutation CheckoutCreate($input: CheckoutCreateInput!) { "
            "checkoutCreate(input: $input) { checkout { id token lines { id quantity variant { id } } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "input": {
                "channel": "{{fixtures.default_channel}}",
                "lines": [{"quantity": 1, "variantId": "{{fixtures.variant_id_for_cart}}"}],
            }
        },
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutLinesAdd",
        "document": (
            "mutation CheckoutLinesAdd($id: ID!, $lines: [CheckoutLineInput!]!) { "
            "checkoutLinesAdd(id: $id, lines: $lines) { checkout { id lines { id quantity } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_checkout_id}}",
            "lines": [{"quantity": 1, "variantId": "{{fixtures.variant_id_for_cart}}"}],
        },
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutLinesUpdate",
        "document": (
            "mutation CheckoutLinesUpdate($id: ID!, $lines: [CheckoutLineUpdateInput!]!) { "
            "checkoutLinesUpdate(id: $id, lines: $lines) { checkout { id lines { id quantity } } "
            "errors { field message code } } }"
        ),
        "variables": {"id": "{{fixtures.default_checkout_id}}", "lines": []},
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutShippingAddressUpdate",
        "document": (
            "mutation CheckoutShippingAddressUpdate($id: ID!, $shippingAddress: AddressInput!) { "
            "checkoutShippingAddressUpdate(id: $id, shippingAddress: $shippingAddress) { "
            "checkout { id shippingAddress { city country { code } } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_checkout_id}}",
            "shippingAddress": {
                "firstName": "Harness",
                "lastName": "Customer",
                "streetAddress1": "1 Test St",
                "city": "Test City",
                "postalCode": "12345",
                "country": "US",
            },
        },
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutDeliveryMethodUpdate",
        "document": (
            "mutation CheckoutDeliveryMethodUpdate($id: ID!, $deliveryMethodId: ID!) { "
            "checkoutDeliveryMethodUpdate(id: $id, deliveryMethodId: $deliveryMethodId) { "
            "checkout { id deliveryMethod { ... on ShippingMethod { id name } } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_checkout_id}}",
            "deliveryMethodId": "{{fixtures.placeholder_id}}",
        },
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutEmailUpdate",
        "document": (
            "mutation CheckoutEmailUpdate($id: ID!, $email: String!) { "
            "checkoutEmailUpdate(id: $id, email: $email) { checkout { id email } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_checkout_id}}",
            "email": "harness-storefront-customer@example.com",
        },
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutComplete",
        "document": (
            "mutation CheckoutComplete($id: ID!) { "
            "checkoutComplete(id: $id) { order { id number status } "
            "errors { field message code } } }"
        ),
        "variables": {"id": "{{fixtures.default_checkout_id}}"},
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutCustomerAttach",
        "document": (
            "mutation CheckoutCustomerAttach($id: ID!, $customerId: ID!) { "
            "checkoutCustomerAttach(id: $id, customerId: $customerId) { checkout { id user { id } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_checkout_id}}",
            "customerId": "{{fixtures.storefront_customer_id}}",
        },
        "auth_context": "customer",
    },
    {
        "operation_name": "Me",
        "document": (
            "query Me { me { id email firstName lastName defaultShippingAddress { id city } } }"
        ),
        "variables": {},
        "auth_context": "customer",
    },
    {
        "operation_name": "AccountAddressCreate",
        "document": (
            "mutation AccountAddressCreate($input: AddressInput!) { "
            "accountAddressCreate(input: $input) { address { id city country { code } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "input": {
                "firstName": "Harness",
                "lastName": "Storefront",
                "streetAddress1": "2 Account St",
                "city": "Account City",
                "postalCode": "54321",
                "country": "US",
            }
        },
        "auth_context": "customer",
    },
    {
        "operation_name": "AccountUpdate",
        "document": (
            "mutation AccountUpdate($input: AccountInput!) { "
            "accountUpdate(input: $input) { user { id firstName lastName } "
            "errors { field message code } } }"
        ),
        "variables": {"input": {"firstName": "Harness", "lastName": "Updated"}},
        "auth_context": "customer",
    },
    {
        "operation_name": "CheckoutByToken",
        "document": (
            "query CheckoutByToken($token: UUID!) { checkout(token: $token) { id token lines { id quantity } } }"
        ),
        "variables": {"token": "{{fixtures.default_checkout_token}}"},
        "auth_context": "anonymous",
    },
    {
        "operation_name": "CheckoutShippingMethods",
        "document": (
            "query CheckoutShippingMethods($id: ID!) { checkout(id: $id) { "
            "availableShippingMethods { id name price { amount currency } } } }"
        ),
        "variables": {"id": "{{fixtures.default_checkout_id}}"},
        "auth_context": "anonymous",
    },
    {
        "operation_name": "DraftOrderCreate",
        "document": (
            "mutation DraftOrderCreate($input: DraftOrderCreateInput!) { "
            "draftOrderCreate(input: $input) { order { id number status } "
            "errors { field message code } } }"
        ),
        "variables": {
            "input": {
                "channelId": "{{fixtures.default_channel_id}}",
                "user": "{{fixtures.default_customer_id}}",
            }
        },
        "auth_context": "staff",
    },
    {
        "operation_name": "OrderLineCreate",
        "document": (
            "mutation OrderLineCreate($id: ID!, $input: OrderLineCreateInput!) { "
            "orderLineCreate(id: $id, input: $input) { order { id lines { id quantity } } "
            "errors { field message code } } }"
        ),
        "variables": {
            "id": "{{fixtures.default_order_id}}",
            "input": {"variantId": "{{fixtures.default_variant_id}}", "quantity": 1},
        },
        "auth_context": "staff",
    },
]
