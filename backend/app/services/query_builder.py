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


def build_query_with_schema(
    endpoint_name: str,
    kind: str,
    schema_fields: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """Build a probe query using introspection arg metadata when available."""
    from app.services.test_runner import build_query

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
