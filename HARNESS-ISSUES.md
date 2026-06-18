# Harness-Side Issues

Baseline run against custom Saleor (3.23.7) at `http://192.168.31.237:8000/graphql/`
on 2026-06-18.

**Result: 856 total — 829 pass, 13 fail, 14 skip, 0 warn**

> **Note:** Failures caused by custom backend `productVariantCreate` database errors
> ([SALEOR-ISSUES.md](SALEOR-ISSUES.md) S1) are out of harness scope. Re-run against
> a fixed backend after Saleor-side repairs.

---

## Issue H1: Static fixture IDs override live-captured entities

**Status:** Verified fixed (commit `695c7a8`, regression test in `test_fixture_resolver.py`)
**Severity:** High — blocked 18 of 27 failures

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

**File:** [`backend/app/services/fixture_resolver.py`](backend/app/services/fixture_resolver.py)

---

## Issue H2: `_ensure_reference_product` doesn't handle product-without-variants

**Status:** Verified fixed (commit `695c7a8`, test in `test_reference_seed_harness.py`)
**Severity:** High

### Problem

`_ensure_reference_product()` queries the product by slug. If the product
exists but has **zero variants**, the function skips variant creation (the
`if variants:` block) and falls through to try creating a **duplicate** product
with the same slug. This fails silently, and `default_variant_id` is never set.

### Fix

When the product exists but has no variants, create one via
`productVariantCreate` before continuing.

**File:** [`backend/app/services/reference_seed.py`](backend/app/services/reference_seed.py)

---

## Issue H3: Scenario enrichment error handler references undefined `start`

**Status:** Verified fixed (commit `695c7a8`)
**Severity:** Medium

### Problem

The `ScenarioEnrichmentError` handler in `_test_endpoint()` referenced
`time.time() - start`, but `start` is defined **after** the enrichment block.
This caused `UnboundLocalError` when enrichment failed.

### Fix

Removed `response_time_ms` from the enrichment error return dict.

**File:** [`backend/app/services/test_runner.py`](backend/app/services/test_runner.py)

---

## Issue H4: sf-accountupdate probe fails with "Account not found"

**Status:** Fixed
**Severity:** Medium

### Problem

`sf-accountupdate` sends `accountUpdate` with `auth_context: customer`.
`apply_bundle_setup()` runs an `accountUpdate` preamble step with `auth: customer`,
but `_run_setup_mutation()` only refreshed the **staff** token — customer setup
mutations were sent without a Bearer token.

Secondary issue: `ensure_customer_token()` defaulted to `default-channel` while
harness topology uses `harness-channel`.

### Fix

1. `_run_setup_mutation()` now calls `_ensure_auth_for_context(auth_context)` before posting.
2. Customer registration uses `harness-channel` (default in `saleor_auth.py` and bundle_setup).
3. Test: `test_sf_accountupdate_setup_uses_customer_auth_for_profile_step` in `test_bundle_setup.py`.

**Files:** [`test_runner.py`](backend/app/services/test_runner.py), [`saleor_auth.py`](backend/app/services/saleor_auth.py)

---

## Issue H5: sitesettings schema structural mismatch

**Status:** Fixed
**Severity:** Low

### Problem

`sitesettings` golden expects `useLegacyShippingZoneStockAvailability: true`.
Fresh/custom Saleor instances often return `false` because harness seed no longer
set this flag after `demo_seed` was trimmed.

### Fix

Added `_ensure_shop_settings()` to `ensure_certification_topology()` — idempotently
enables legacy shipping-zone stock availability via `shopSettingsUpdate`.

**File:** [`backend/app/services/reference_seed.py`](backend/app/services/reference_seed.py)

---

## Issue H6: product-lifecycle scenario schema mismatches

**Status:** Fixed
**Severity:** Low

### Problem

Scenario goldens include `"errors": []` on success mutations. `extract_schema()`
only descends into non-empty arrays, so backends that omit empty `errors` keys
produced structural schema mismatches.

### Fix

Forgive missing `.errors` paths when golden records an empty errors array
(no `errors[0]` child paths in golden schema). Also treat `.id` fields as
compatible when golden uses short Relay IDs (`string`) and live responses
use longer base64 (`global_id`).

**File:** [`backend/app/services/schema_compare.py`](backend/app/services/schema_compare.py)

---

## Issue H7: orderLinesCreate uses hardcoded Order ID

**Status:** Resolved via H1
**Severity:** Low (blocked by H1)

### Problem

`orderLinesCreate` used a previously-seeded order ID but failed because
`default_variant_id` was missing (blocked by H1 static fixture override).

### Fix

Resolves once H1 clears static entity keys and runtime seed creates a variant.

---

## Summary of original 27 failures

| # | Endpoint | Status | Category | Root cause |
|---|----------|--------|----------|------------|
| 1 | sitesettings | fixed (H5) | schema_mismatch | H5 |
| 2-6 | sf-checkout* | skip if no variant | data_prerequisite | H1 + Saleor S1 |
| 7 | sf-accountupdate | fixed (H4) | real_bug | H4 |
| 8-16 | sf-*, productvariant*, order* | skip if no variant | data_prerequisite | H1 + Saleor S1 |
| 17 | scenario/01_checkout_create | cascade | assertion_fail | H1 + Saleor S1 |
| 18-21 | checkout scenario steps | cascade | enrichment_error | H1 + Saleor S1 |
| 22 | orderLinesCreate | fixed via H1 | assertion_fail | H1 |
| 23-27 | product-lifecycle scenario | fixed (H6) | schema_mismatch | H6 |
