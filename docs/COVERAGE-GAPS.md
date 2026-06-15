# Coverage gaps and roadmap

This document records **what official certification covers today** and **what is intentionally out of scope** (or not yet built). Use it when planning corpus expansion, Storefront support, or interpreting a passing `just baseline` run.

Related: [COMPATIBILITY.md](COMPATIBILITY.md) (certification gates), [REFERENCE-SEED.md](REFERENCE-SEED.md) (L3 fixtures).

## Coverage model (current pin: Saleor 3.23.7)

| Layer | Location | Count | Role |
|-------|----------|-------|------|
| **L1** | `reference/corpora/saleor-3.23.7/probes/` | **387** | One synthetic probe per schema query/mutation (introspection-driven) |
| **L3 Dashboard** | `reference/client-bundles/dashboard-3.23.6/` | **415 recorded**, **415 certified** | Real Dashboard GraphQL documents + golden responses |
| **L3 Storefront** | `reference/client-bundles/storefront-3.23.6/` | **31 recorded** | Storefront + SDK GraphQL documents + golden responses |
| **L4 Scenarios** | `reference/scenarios/` | **15 steps** (3 flows) | product (6), checkout (6), order (3) |
| **Variants** | `reference/variants/` | **3** (`productCreate`) | Valid/invalid input matrices |
| **Dynamic probes** | `reference/dynamic/` + built-ins | **5** | Anti-static-response |
| **Certification total** | `full+scenarios` scope | **856** | L1 + L3 dashboard + L3 storefront + scenarios + variants + dynamic |

`just baseline` proves **100%** SGRC match on official Saleor under `full+scenarios`. Deprecated L3 bundles are removed from the corpus — not counted in reports.

```text
                    ┌─────────────────────────────────────┐
  Saleor 3.23.7     │  L1: 387 ops (synthetic inputs)    │  ← schema completeness
  introspection     └─────────────────────────────────────┘
                    ┌─────────────────────────────────────┐
  Dashboard 3.23.6  │  L3: 415 bundles (real documents)  │  ← Dashboard UX shapes
  vendor GraphQL    └─────────────────────────────────────┘
                    ┌─────────────────────────────────────┐
  Storefront 3.23.6 │  L3: 31 bundles (recorded)            │  ← Storefront UX shapes
  (saleor-storefront)└─────────────────────────────────────┘
```

## What L1 already includes (Storefront-relevant ops)

L1 is **not** missing most Storefront **operation names**. The corpus includes checkout, account, catalog, and shop operations, for example:

- Checkout: `checkoutCreate`, `checkoutLinesAdd`, `checkoutComplete`, …
- Account: `accountRegister`, `tokenCreate`, `me`, `confirmAccount`, …
- Catalog: `products`, `product`, `categories`, `collections`, `menus`, `pages`, …

L1 replays **minimal/synthetic** GraphQL (often validation or permission errors), not the fragment-heavy documents Storefront sends. A backend can pass L1 while still breaking the official Storefront app.

Example: `checkoutCreate` L1 sends empty input and golden-records a schema validation error — not a real cart line payload.

## Gap 1 — Storefront L3 breadth (expanded)

**Status:** **31** bundles (16 vendor + 15 SDK checkout/account documents).

| Piece | Status |
|-------|--------|
| Vendor source | `reference/vendor/saleor-storefront-3.23.6/` |
| SDK documents | `backend/app/services/storefront_sdk_documents.py` |
| Client bundles | `reference/client-bundles/storefront-3.23.6/` (`sf-` bundle IDs) |
| Import pipeline | `scan_sdk_storefront_bundles()` + `just patch-corpus --sync-client` |
| Certification scope | `full+scenarios` includes all **31** recorded storefront bundles |

**Remaining:** Record golden on official Saleor for new SDK bundles; expand as Storefront vendor pin grows.

## Gap 2 — Customer-session auth replay (partial)

**Status:** Customer JWT replay + **storefront session preamble** (`accountUpdate` + anonymous checkout chain) run automatically when `DEMO_SEED_PROFILE=saleor_demo`.

**Remaining:** Not all customer-context operations have customer-auth golden recorded. Staff token remains the default for dashboard bundles. Expand customer-tagged golden capture for storefront account/checkout flows.

## Gap 3 — Multi-step scenario chains (partial)

**Status:** L4 scenario framework + **product lifecycle**, **checkout lifecycle**, and **order lifecycle** scenarios.

| Scenario | Steps | Auth |
|----------|-------|------|
| `product-lifecycle` | 6 | staff |
| `checkout-lifecycle` | 6 | anonymous → customer |
| `order-lifecycle` | 3 | staff |

Record goldens: `just patch-corpus --scenarios checkout-lifecycle,order-lifecycle` on official Saleor.

**Remaining:** Record goldens for new checkout steps 05–06 (`just patch-corpus --scenarios checkout-lifecycle` on official Saleor). Optional payment gateway fixture for `checkoutComplete` success golden.

## Gap 4 — Deprecated L3 bundles (removed)

**11** schema-dead dashboard bundles were **removed** from the corpus (`just patch-corpus --remove …`). They are not executed, not scored, and reports surface `excluded_l3_bundles` / `not_counted_note` for AI agents when any legacy exclusion metadata remains.

Removed IDs: `salelist`, `saledetails`, `updatesaletranslations`, `ordersettings`, `ordersettingsupdate`, `productexport`, `exportgiftcards`, `user`, `userwithoutdetails`, `welcomepageanalytics`, `welcomepageactivities`.

## Gap 5 — L3 depth vs L1 breadth (Dashboard)

| Area | L1 | L3 Dashboard |
|------|----|--------------|
| `productVariantStocks*` | Probed (synthetic) | No dedicated dashboard bundle parity (roadmap) |
| `productBulkCreate` | Probed | Partial / alignment TBD |
| Channel `orderSettings` nested fields | N/A at L1 root | Covered in channel bundles (certified) |

## Gap 6 — Fixture-dependent L3 vs stateless L1

L3 dashboard bundles substitute `{{fixtures.*}}` IDs (see [REFERENCE-SEED.md](REFERENCE-SEED.md)). External backends must seed equivalent entities or L3 failures may be **missing data**, not SGRC incompatibility.

L1 does not require seeded data.

## Gap 7 — Runtime and integration behavior (outside GraphQL replay)

Certification replays HTTP GraphQL JSON. It does **not** certify:

| Behavior | Today |
|----------|-------|
| Async webhook delivery to app URLs | Only `webhookTrigger` / dry-run style probes |
| Celery/worker jobs (export completion, emails) | Not end-to-end |
| Payment plugin gateways (Stripe, Adyen, …) | Mutation shape only, not live gateway |
| `fileUpload` multipart | L1 probe exists; not full multipart fidelity |
| GraphQL subscriptions | Not in reference schema |
| Dashboard UI / Storefront UI | Manual smoke only (see README) |

## Gap 8 — Harness and ops

| Item | Status |
|------|--------|
| Automated API certification test (POST run → assert certified) | `just test-e2e` (requires `SALEOR_E2E=1` + full stack) |
| GitHub CI | Intentionally absent — local `just baseline` + pytest |
| L2 static catalog in `test_runner.py` (~108 ops) | Legacy / discovery; not the certification path |

## Priority matrix (for later planning)

| Gap | Severity if Storefront breaks | Severity if Dashboard breaks | Effort (rough) |
|-----|------------------------------|------------------------------|----------------|
| Storefront L3 breadth | Medium | Low | Medium (expand vendor import) |
| Customer JWT golden coverage | Medium | Medium | Medium |
| Scenario chains (orders/checkout) | Medium | Medium | Medium–large |
| 11 excluded dashboard bundles | Low | Low (until Sale API / exports return) | Small on version bump |
| Stock L3 parity | Low | Medium | Medium |
| Runtime/webhooks/payments | Medium (different failure class) | Medium | Large (new test types) |

## What “certified” means today (summary)

A backend that passes `just baseline` / `full+scenarios` with 100% SGRC:

- Implements every **3.23.7** schema operation at L1 synthetic replay level.
- Matches **415** real **Dashboard** GraphQL documents with seeded fixtures.
- Matches **31** **Storefront** GraphQL documents with seeded fixtures.
- Passes **13** scenario steps (product, checkout, order lifecycles) and **productCreate** variant probes.
- Passes **5** dynamic probes (runtime echo validation).
- Passes SGRC Tier 1 (and Tier 2 when `SGRC_TIER2_GATE=true`).
- Passes L3 **document schema gate** (nested field/type validation in client documents).

It does **not** yet guarantee:

- Full **customer-session** golden replay for all account/checkout ops beyond recorded storefront bundles.
- **Payment/checkoutComplete** scenario step when gateway fixtures exist.
- **Async** worker, webhook, or payment-gateway integration behavior.

When Storefront or Dashboard breaks a certified backend, platform rules require **adding probes/bundles**, not weakening Tier 1 — see workspace rules and [COMPATIBILITY.md](COMPATIBILITY.md).

## Hardening changes (this release)

The testing system hardening plan has been implemented with the following changes:

### Phase 1A — Stop false failures
- **Deprecated type auto-exclusion**: L3 bundles referencing `Sale`, `SaleTranslatableContent`, `SaleTranslation`, etc. are automatically excluded from scoring.
- **Runtime fixture resolver**: `POST /api/runs/validate` pre-flight endpoint checks API reachability, version match, and fixture entity presence.
- **Structured exclusion reporting**: `failure_category` field on all results (compatible, real_bug, deprecated_excluded, data_prerequisite, seed_prerequisite, missing_golden). Effective score excludes deprecated + data-prerequisite + seed-prerequisite from denominator.

### Phase 1B — Close bypass holes
- **Missing-golden auto-pass removed**: Scenario and variant probes no longer auto-pass without golden reference (gated by `SGRC_ALLOW_ASSERTION_ONLY=false`).
- **Variant matrix variables**: `blank_name` variant now sends proper variables from `matrix.json`.
- **Fixture KeyError handling**: Silent fallback replaced with explicit skip + `failure_category=data_prerequisite`.

### Phase 2 — Anti-static-response
- **Dynamic probes**: 5 runtime-generated probes (product/category/collection/channel create + not-found query) validate echo/structural/semantic_error modes.
- **Input binding checks**: `input_binding.py` service validates success mutations echo input values.
- **Tightened stateful policy**: L1 error probes always stateless; L3 success bundles never blanket stateful; stateful drift allowed only for L1 success queries with no mismatches.
- **Narrowed error semantics**: Stateless probes require regex/message_pattern match, not just category bucket.

### Phase 3 — Reporting and perf
- **Field-level diff**: `field_compare.py` now includes value comparison for scalar mismatches; `summarize_field_diffs()` for report display.
- **Parallel probe tiers**: `probe_tiers.py` classifies endpoints into Tier 0 (parallel read), Tier 1 (sequential mutate), Tier 2 (scenario ordered), Tier 3 (dynamic sequential).
- **Version hard gate**: `version_hard_gate_check()` fails certification on major/minor mismatch; patch drift requires `ALLOW_PATCH_DRIFT=true`.
