"""
GraphQL schema introspection and comparison helpers.
"""

from __future__ import annotations

from typing import Any

import httpx

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { fields { name } }
    mutationType { fields { name } }
  }
}
"""

FULL_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
    directives {
      name
      description
      locations
      args {
        ...InputValue
      }
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
    }
  }
}
"""


def normalize_graphql_url(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/graphql"):
        if url.endswith("graphql"):
            url = url + "/"
        else:
            url = url + "/graphql"
    if not url.endswith("/"):
        url = url + "/"
    return url


async def introspect_saleor(
    url: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Return query and mutation field names from introspection."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    graphql_url = normalize_graphql_url(url)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            graphql_url,
            json={"query": INTROSPECTION_QUERY},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    errors = data.get("errors")
    if errors:
        raise RuntimeError(errors[0].get("message", "Introspection failed"))

    schema = data.get("data", {}).get("__schema", {})
    queries = [
        f["name"]
        for f in (schema.get("queryType") or {}).get("fields") or []
    ]
    mutations = [
        f["name"]
        for f in (schema.get("mutationType") or {}).get("fields") or []
    ]
    return {"queries": queries, "mutations": mutations}


async def introspect_full_schema(
    url: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Return full GraphQL introspection result for document validation."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    graphql_url = normalize_graphql_url(url)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            graphql_url,
            json={"query": FULL_INTROSPECTION_QUERY},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    errors = data.get("errors")
    if errors:
        raise RuntimeError(errors[0].get("message", "Full introspection failed"))

    return data


def compare_schema(
    introspected: dict[str, list[str]],
    reference_queries: list[str],
    reference_mutations: list[str],
) -> dict[str, list[str]]:
    """Compare introspected names against static reference lists."""
    iq = set(introspected.get("queries", []))
    im = set(introspected.get("mutations", []))
    rq = set(reference_queries)
    rm = set(reference_mutations)

    static_q = [n for n in rq if n not in iq]
    static_m = [n for n in rm if n not in im]
    extra_q = sorted(iq - rq)
    extra_m = sorted(im - rm)

    return {
        "missing_queries": static_q,
        "missing_mutations": static_m,
        "extra_queries": extra_q,
        "extra_mutations": extra_m,
    }


def compare_two_introspections(
    target: dict[str, list[str]],
    reference: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Field-level drift between target and reference APIs."""
    tq, tm = set(target.get("queries", [])), set(target.get("mutations", []))
    rq, rm = set(reference.get("queries", [])), set(reference.get("mutations", []))

    return {
        "target_only_queries": sorted(tq - rq),
        "target_only_mutations": sorted(tm - rm),
        "reference_only_queries": sorted(rq - tq),
        "reference_only_mutations": sorted(rm - tm),
        "shared_queries": sorted(tq & rq),
        "shared_mutations": sorted(tm & rm),
    }


def schema_gate_diff(
    target: dict[str, list[str]],
    reference: dict[str, list[str]],
    *,
    source: str = "golden",
) -> dict[str, Any]:
    """Build schema_diff for the compatibility gate (reference ops must exist on target)."""
    from app.services.deprecated_scanner import filter_deprecated_schema_ops

    filtered_reference = {
        "queries": list(reference.get("queries") or []),
        "mutations": filter_deprecated_schema_ops(list(reference.get("mutations") or [])),
    }
    drift = compare_two_introspections(target, filtered_reference)
    return {
        "missing_queries": drift["reference_only_queries"],
        "missing_mutations": drift["reference_only_mutations"],
        "extra_queries": drift["target_only_queries"],
        "extra_mutations": drift["target_only_mutations"],
        "schema_gate_source": source,
    }
