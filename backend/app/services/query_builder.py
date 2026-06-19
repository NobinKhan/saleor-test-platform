"""
Introspection-aware GraphQL query builder for probe requests.
"""

from __future__ import annotations

from typing import Any

PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000000"


def _unwrap_type(type_info: dict[str, Any] | None) -> dict[str, Any]:
    if not type_info:
        return {}
    while type_info.get("kind") in ("NON_NULL", "LIST"):
        type_info = type_info.get("ofType") or {}
    return type_info


def _arg_type_name(arg: dict[str, Any]) -> str:
    t = _unwrap_type(arg.get("type"))
    return t.get("name") or ""


def _is_required(arg: dict[str, Any]) -> bool:
    return arg.get("type", {}).get("kind") == "NON_NULL"


def _default_scalar_value(type_name: str) -> str:
    if type_name in ("Int", "Float"):
        return "1"
    if type_name == "Boolean":
        return "true"
    if type_name == "ID":
        return f'"{PLACEHOLDER_UUID}"'
    return '"test"'


def build_query(endpoint_name: str, kind: str) -> str:
    """Build a synthetic GraphQL document for golden corpus capture (not certification replay)."""
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
            return f'query {{ {endpoint_name}(first: 1) {{ edges {{ node {{ id }} }} }} }}'

    if endpoint_name == "checkoutCreate":
        return 'mutation { checkoutCreate(input: { channel: "default" }) { checkout { id } errors { field message code } } }'
    if endpoint_name == "checkoutComplete":
        return 'mutation { checkoutComplete(id: "00000000-0000-0000-0000-000000000000") { order { id } errors { field message } } }'
    if endpoint_name == "checkoutAddPromoCode":
        return 'mutation { checkoutAddPromoCode(id: "00000000-0000-0000-0000-000000000000", promoCode: "TEST") { checkout { id } errors { field message } } }'
    if endpoint_name == "checkoutEmailUpdate":
        return 'mutation { checkoutEmailUpdate(id: "00000000-0000-0000-0000-000000000000", email: "test@test.com") { checkout { id } errors { field message } } }'
    if endpoint_name == "accountRegister":
        return 'mutation { accountRegister(input: { email: "test@test.com", password: "Test1234!", channel: "default" }) { user { id email } errors { field message } } }'
    if endpoint_name == "confirmAccount":
        return 'mutation { confirmAccount(email: "test@test.com", token: "testtoken") { user { id } errors { field message } } }'
    if endpoint_name == "requestPasswordReset":
        return 'mutation { requestPasswordReset(email: "test@test.com", channel: "default") { errors { field message } } }'
    if endpoint_name == "resetPassword":
        return 'mutation { resetPassword(token: "testtoken", password: "Test1234!") { user { id } errors { field message } } }'
    if endpoint_name == "productCreate":
        return 'mutation { productCreate(input: { name: "Test", slug: "test-product-xyz", productType: "PHYSICAL" }) { product { id name } errors { field message code } } }'
    if endpoint_name == "categoryCreate":
        return 'mutation { categoryCreate(input: { name: "Test Category", slug: "test-cat-xyz" }) { category { id name } errors { field message } } }'
    if endpoint_name == "collectionCreate":
        return 'mutation { collectionCreate(input: { name: "Test Collection", slug: "test-col-xyz" }) { collection { id name } errors { field message } } }'
    if endpoint_name == "channelCreate":
        return 'mutation { channelCreate(input: { name: "Test Channel", slug: "test-channel-xyz", currencyCode: "USD", isActive: true }) { channel { id name } errors { field message } } }'
    if endpoint_name == "voucherCreate":
        return 'mutation { voucherCreate(input: { code: "TESTXYZ", name: "Test Voucher", discountValueType: PERCENTAGE, discountValue: 10 }) { voucher { id code } errors { field message } } }'
    return f'mutation {{ {endpoint_name}(input: {{}}) {{ errors {{ field message code }} }} }}'


def build_query_with_schema(
    endpoint_name: str,
    kind: str,
    schema_fields: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """Build a probe query using introspection arg metadata when available."""
    if not schema_fields:
        return build_query(endpoint_name, kind)

    fields = schema_fields.get("queries" if kind == "QUERY" else "mutations", [])
    field_info = next((f for f in fields if f.get("name") == endpoint_name), None)
    if not field_info:
        return build_query(endpoint_name, kind)

    args = field_info.get("args") or []
    arg_names = {a["name"] for a in args}

    if kind == "QUERY":
        if "first" in arg_names:
            return f"query {{ {endpoint_name}(first: 1) {{ edges {{ node {{ id }} }} }} }}"
        if "id" in arg_names:
            return f'query {{ {endpoint_name}(id: "{PLACEHOLDER_UUID}") {{ id }} }}'
        if "slug" in arg_names:
            return f'query {{ {endpoint_name}(slug: "test") {{ id }} }}'
        if "token" in arg_names:
            return f'query {{ {endpoint_name}(token: "{PLACEHOLDER_UUID}") {{ id }} }}'
        required_args = [a for a in args if _is_required(a)]
        if required_args:
            parts = []
            for arg in required_args:
                tname = _arg_type_name(arg)
                parts.append(f'{arg["name"]}: {_default_scalar_value(tname)}')
            return f"query {{ {endpoint_name}({', '.join(parts)}) {{ __typename }} }}"
        return f"query {{ {endpoint_name} {{ __typename }} }}"

    if "input" in arg_names:
        return f"mutation {{ {endpoint_name}(input: {{}}) {{ errors {{ field message code }} }} }}"
    required_args = [a for a in args if _is_required(a) and a["name"] != "input"]
    if required_args:
        parts = []
        for arg in required_args:
            tname = _arg_type_name(arg)
            parts.append(f'{arg["name"]}: {_default_scalar_value(tname)}')
        return f"mutation {{ {endpoint_name}({', '.join(parts)}) {{ errors {{ field message }} }} }}"
    return f"mutation {{ {endpoint_name} {{ errors {{ field message }} }} }}"


INTROSPECTION_ARGS_QUERY = """
query IntrospectionArgsQuery {
  __schema {
    queryType {
      fields {
        name
        args {
          name
          type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
        }
      }
    }
    mutationType {
      fields {
        name
        args {
          name
          type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
        }
      }
    }
  }
}
"""


async def introspect_field_args(
    url: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, list[dict[str, Any]]]:
    import httpx

    from app.services.introspection import normalize_graphql_url

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    graphql_url = normalize_graphql_url(url)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            graphql_url,
            json={"query": INTROSPECTION_ARGS_QUERY},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    errors = data.get("errors")
    if errors:
        raise RuntimeError(errors[0].get("message", "Introspection failed"))

    schema = data.get("data", {}).get("__schema", {})
    return {
        "queries": (schema.get("queryType") or {}).get("fields") or [],
        "mutations": (schema.get("mutationType") or {}).get("fields") or [],
    }
