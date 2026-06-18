# Harness-Side Issues

Baseline run against custom Saleor (3.23.7) at `http://192.168.31.237:8000/graphql/`
on 2026-06-18.

**Result: 856 total — 829 pass, 13 fail, 14 skip, 0 warn**

---

## Issue H1: Static fixture IDs override live-captured entities

**Status:** Fixed (in `fixture_resolver.py`)
**Severity:** High — blocks 18 of 27 failures

### Problem

`resolve_fixtures()` loads static fixtures from baked reference files on disk
(`reference/baked/client-bundles/.../fixtures.json`). These contain hardcoded
entity IDs from the original Saleor demo data:

```
default_variant_id:    UHJvZHVjdFZhcmlhbnQ6MQ==  (ProductVariant:1)
default_product_id:    UHJvZHVjdDox              (Product:1)
default_checkout_id:   Q2hlY2tvdXQ6NTJkYjA3ND... (hardcoded checkout)
variant_id_for_cart:   UHJvZHVjdFZhcmlhbnQ6MQ==  (ProductVariant:1)
```

`_apply_captured()` only **adds** keys not already in `resolved` — it never
overrides existing keys. So the static IDs persist even when the live Saleor
has completely different entities (or none at all).

The seed functions (`_ensure_reference_product`, etc.) check
`fixtures.get("default_variant_id")` and skip creation if the key exists,
even though the referenced entity doesn't exist on the target.

### Fix

Clear entity-specific keys from `resolved` before seeding when `RUNTIME_SEED=true`:

```python
_ENTITY_KEYS = {
    "default_product_id", "default_variant_id", "variant_id_for_cart",
    "default_checkout_id", "default_checkout_token",
    "default_customer_id", "default_order_id",
    "default_product_type_id", "default_warehouse_id",
}
for k in _ENTITY_KEYS:
    resolved.pop(k, None)
```

**File:** `backend/app/services/fixture_resolver.py:142-155`

---

## Issue H2: `_ensure_reference_product` doesn't handle product-without-variants

**Status:** Fixed (in `reference_seed.py`)
**Severity:** High

### Problem

`_ensure_reference_product()` queries the product by slug. If the product
exists but has **zero variants**, the function skips variant creation (the
`if variants:` block) and falls through to try creating a **duplicate** product
with the same slug. This fails silently, and `default_variant_id` is never set.

### Fix

When the product exists but has no variants, create one via
`productVariantCreate` before continuing:

```python
if not variants:
    variant_data = await _gql(
        client, url=url, headers=headers,
        query="mutation($input: ProductVariantCreateInput!) { ... }",
        variables={"input": {"product": existing["id"], "sku": "harness-ref-sku",
                             "name": "Harness Reference Variant", "attributes": []}},
        allow_errors=True, error_log=error_log,
    )
    ...
```

**File:** `backend/app/services/reference_seed.py:537-562`

---

## Issue H3: Scenario enrichment error handler references undefined `start`

**Status:** Fixed (in `test_runner.py`)
**Severity:** Medium

### Problem

The `ScenarioEnrichmentError` handler in `_test_endpoint()` references
`time.time() - start`, but `start` is defined **after** the enrichment block
(line 807). This causes `UnboundLocalError` when enrichment fails.

### Fix

Remove `"response_time_ms"` from the enrichment error return dict.

**File:** `backend/app/services/test_runner.py:751-768`

---

## Issue H4: sf-accountupdate probe fails with "Account not found"

**Status:** Not fixed — needs investigation
**Severity:** Medium

### Problem

`sf-accountupdate` sends `accountUpdate` with `auth_context: customer`.
The probe fails with `"Account not found"` even though the customer
(`harness-storefront-customer@example.com`, User:2) exists on the Saleor.

The likely cause is that `self._customer_token` is `None` when
`_auth_headers("customer")` is called, so the request goes without
authentication. `_ensure_auth_for_context()` may not be called before
the bundle_setup's `accountUpdate` step.

### Reproduction

```json
{
  "query": "mutation AccountUpdate($input: AccountInput!) { accountUpdate(input: $input) { user { id firstName lastName } errors { field message code } } }",
  "variables": {"input": {"firstName": "Harness", "lastName": "Updated"}}
}
```

Response: `"Account not found"` with `code: "NOT_FOUND"`.

### Suggested fix

Ensure `_ensure_auth_for_context(auth_context="customer")` is called
**before** `apply_bundle_setup()` for bundles with `auth_context: customer`.

---

## Issue H5: sitesettings schema structural mismatch

**Status:** Not fixed — needs investigation
**Severity:** Low

### Problem

`sitesettings` golden comparison fails with:
```
Schema mismatch: 1 structural diffs, 1 volatile diffs
```

The golden response for `sitesettings` has a specific set of fields in the
`shop` query. The custom Saleor returns a response with 1 structural
difference (a field type mismatch or extra/missing field) and 1 volatile
difference (country name drift).

### Next steps

Run the comparison in verbose mode to identify the exact structural diff:

```python
from app.services.schema_compare import compare_schemas, extract_schema
# Compare golden vs actual to find the differing path
```

---

## Issue H6: product-lifecycle scenario schema mismatches

**Status:** Not fixed — needs investigation
**Severity:** Low

### Problem

All 5 steps of the `product-lifecycle` scenario succeed (mutations work)
but each step's golden comparison fails with:
```
Scenario schema mismatch: Schema mismatch: 1 structural diffs, 0 volatile diffs
```

The custom Saleor likely returns additional or different fields in the
`productCreate`, `product`, `productUpdate`, `productDelete` responses
compared to the golden recorded from the standard Saleor 3.23.6.

### Next steps

Compare the actual response schema against the golden schema for one step
to identify the exact structural difference.

---

## Issue H7: orderLinesCreate uses hardcoded Order ID

**Status:** Blocked by missing order
**Severity:** Low (blocked by H1)

### Problem

`orderLinesCreate` probe uses `T3JkZXI6OTY0NzhjYWItNzNjNy00OTQ4LWE5MzQtYTYxYWJlM2NlNGU3`
which is a previously-seeded order. The order exists on this Saleor but the
probe fails because it also uses `{{fixtures.default_variant_id}}` which is
missing (blocked by H1).

### Fix

This should resolve once H1 is fixed and the variant exists.

---

## Summary of all 27 failures

| # | Endpoint | Status | Category | Root cause |
|---|----------|--------|----------|------------|
| 1 | sitesettings | fail | schema_mismatch | H5 |
| 2-6 | sf-checkout* | skip | data_prerequisite | H1 (no variant) |
| 7 | sf-accountupdate | fail | real_bug | H4 |
| 8-16 | sf-*, productvariant*, order* | skip | data_prerequisite | H1 (no variant) |
| 17 | scenario/01_checkout_create | fail | assertion_fail | H1 (no variant) |
| 18 | scenario/02_checkout_lines_add | fail | assertion_fail | cascade from 17 |
| 19 | scenario/03_checkout_shipping | fail | assertion_fail | cascade from 17 |
| 20 | scenario/05_delivery_method | fail | enrichment_error | cascade from 17 |
| 21 | scenario/06_checkout_complete | fail | enrichment_error | cascade from 17 |
| 22 | orderLinesCreate | fail | assertion_fail | H1 (no variant) |
| 23-27 | product-lifecycle scenario | fail | schema_mismatch | H6 |
