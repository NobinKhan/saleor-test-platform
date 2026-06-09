# Coverage gaps and roadmap

This document records **what official certification covers today** and **what is intentionally out of scope** (or not yet built). Use it when planning corpus expansion, Storefront support, or interpreting a passing `just baseline` run.

Related: [COMPATIBILITY.md](COMPATIBILITY.md) (certification gates), [REFERENCE-SEED.md](REFERENCE-SEED.md) (L3 fixtures).

## Coverage model (current pin: Saleor 3.23.7)

| Layer | Location | Count | Role |
|-------|----------|-------|------|
| **L1** | `reference/corpora/saleor-3.23.7/probes/` | **388** | One synthetic probe per schema query/mutation (introspection-driven) |
| **L3 Dashboard** | `reference/client-bundles/dashboard-3.23.6/` | **428 recorded**, **417 certified** | Real Dashboard GraphQL documents + golden responses |
| **Certification total** | `full+client` scope | **805** | 388 L1 + 417 schema-compatible L3 bundles |

`just baseline` proves **805/805** SGRC match on official Saleor. That is **Dashboard-shaped** client certification plus **operation-level** API probes — not full Storefront client replay.

```text
                    ┌─────────────────────────────────────┐
  Saleor 3.23.7     │  L1: 388 ops (synthetic inputs)    │  ← schema completeness
  introspection     └─────────────────────────────────────┘
                    ┌─────────────────────────────────────┐
  Dashboard 3.23.6  │  L3: 417 bundles (real documents)  │  ← Dashboard UX shapes
  vendor GraphQL    └─────────────────────────────────────┘
                    ┌─────────────────────────────────────┐
  Storefront        │  L3: not implemented                 │  ← largest gap
  (saleor-storefront)└─────────────────────────────────────┘
```

## What L1 already includes (Storefront-relevant ops)

L1 is **not** missing most Storefront **operation names**. The corpus includes checkout, account, catalog, and shop operations, for example:

- Checkout: `checkoutCreate`, `checkoutLinesAdd`, `checkoutComplete`, …
- Account: `accountRegister`, `tokenCreate`, `me`, `confirmAccount`, …
- Catalog: `products`, `product`, `categories`, `collections`, `menus`, `pages`, …

L1 replays **minimal/synthetic** GraphQL (often validation or permission errors), not the fragment-heavy documents Storefront sends. A backend can pass L1 while still breaking the official Storefront app.

Example: `checkoutCreate` L1 sends empty input and golden-records a schema validation error — not a real cart line payload.

## Gap 1 — Storefront L3 (highest priority for Storefront parity)

**Status:** Not implemented.

**Missing pieces:**

| Piece | Dashboard (exists) | Storefront (missing) |
|-------|-------------------|----------------------|
| Vendor source | `reference/vendor/saleor-dashboard-3.23.6/` | No `reference/vendor/saleor-storefront-*` |
| Client bundles | `reference/client-bundles/dashboard-3.23.6/` | No `reference/client-bundles/storefront-*` |
| Import pipeline | `just patch-corpus --sync-client` (dashboard) | No storefront import |
| Fixtures | `fixtures.json` (product/order/customer IDs) | No storefront-specific fixtures (checkout token, channel slug, cart state) |
| Certification scope | `full+client` | No `full+client+storefront` (or equivalent) |

**Suggested follow-up work:**

1. Vendor `saleor-storefront` at a pinned tag aligned with the Saleor API pin.
2. Mirror the dashboard bundle importer for storefront `.graphql` documents.
3. Extend `seed-reference` for storefront fixture keys (checkout ID, channel slug, line items).
4. Record golden on official Saleor; add schema gate for storefront root fields.
5. Extend baseline / `test_runner_scope` counts when storefront bundles land.

## Gap 2 — Customer-session auth replay

**Status:** Staff admin JWT is the default for certification runs (`tokenCreate` with admin credentials).

Customer-context mutations are captured with staff token and often golden as **expected auth failures**, not as a logged-in customer session. See `CUSTOMER_CONTEXT_OPS` in `backend/app/services/reference_capture.py`.

**Impact:** Account and checkout flows that require a **customer JWT** (as Storefront uses) are not fully replayed in compatibility mode.

**Suggested follow-up:**

- Capture/replay path that obtains a customer token (`accountRegister` / `tokenCreate` as customer).
- Separate golden profiles for customer-context ops under customer auth.
- Storefront L3 bundles tagged with `auth_context: customer` where appropriate.

## Gap 3 — Multi-step scenario chains

**Status:** Roadmap only. Today probes and bundles are overwhelmingly **single-shot**.

**Not covered as chained scenarios:**

- Product lifecycle: create → read → update → delete (with consistent IDs)
- Order lifecycle: draft → confirm → fulfill → refund
- Checkout lifecycle: create cart → add lines → shipping → payment → complete

L1 stateless probes and one-off L3 bundles can miss bugs that only appear across dependent mutations.

## Gap 4 — Eleven L3 bundles recorded but excluded from certification

**428** dashboard bundles are recorded; the **L3 schema gate** drops **11** whose **root** query/mutation fields are not on Saleor **3.23.7** introspection (Dashboard 3.23.6 vendor still references removed or Apollo-local APIs).

| Bundle ID | Missing root field(s) | Notes |
|-----------|----------------------|-------|
| `salelist` | `sales` (QUERY) | Deprecated Sale API |
| `saledetails` | `sale` (QUERY) | Deprecated Sale API |
| `updatesaletranslations` | `saleTranslate` (MUTATION) | Deprecated Sale API |
| `ordersettings` | `orderSettings` (QUERY) | Replaced by channel-scoped settings |
| `ordersettingsupdate` | `orderSettingsUpdate` (MUTATION) | Replaced by channel-scoped settings |
| `productexport` | `exportProducts` (MUTATION) | Not on 3.23.7 schema |
| `exportgiftcards` | `exportGiftCards` (MUTATION) | Not on 3.23.7 schema |
| `user` | `authenticated`, `authenticating` (QUERY) | Apollo `@client` fields — not server schema |
| `userwithoutdetails` | `authenticated`, `authenticating` (QUERY) | Apollo `@client` fields |
| `welcomepageanalytics` | `ordersTotal` (QUERY) | Dashboard analytics query not on API pin |
| `welcomepageactivities` | `homepageEvents` (QUERY) | Dashboard home query not on API pin |

These bundles remain on disk for drift tracking; they are **not** in the **805** certification set until the pinned Saleor version regains those fields or the dashboard vendor drops them.

**L1 note:** `exportProducts` has no L1 probe on 3.23.7 for the same reason.

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
| Automated API certification test (POST run → assert certified) | Recommended follow-up; not implemented |
| GitHub CI | Intentionally absent — local `just baseline` + pytest |
| L2 static catalog in `test_runner.py` (~108 ops) | Legacy / discovery; not the certification path |

## Priority matrix (for later planning)

| Gap | Severity if Storefront breaks | Severity if Dashboard breaks | Effort (rough) |
|-----|------------------------------|------------------------------|----------------|
| Storefront L3 | **High** | Low | Large (new vendor + pipeline + fixtures) |
| Customer JWT replay | **High** | Medium | Medium |
| Scenario chains | Medium | Medium | Medium–large |
| 11 excluded dashboard bundles | Low | Low (until Sale API / exports return) | Small on version bump |
| Stock L3 parity | Low | Medium | Medium |
| Runtime/webhooks/payments | Medium (different failure class) | Medium | Large (new test types) |

## What “certified” means today (summary)

A backend that passes `just baseline` / `full+client` with 100% SGRC:

- Implements every **3.23.7** schema operation at L1 synthetic replay level.
- Matches **417** real **Dashboard** GraphQL documents with seeded fixtures.
- Passes SGRC Tier 1 (and Tier 2 when `SGRC_TIER2_GATE=true`).

It does **not** yet guarantee:

- Official **Storefront** GraphQL document compatibility.
- Full **customer-session** checkout/account replay.
- **Stateful multi-step** commerce scenarios.
- **Async** worker, webhook, or payment-gateway integration behavior.

When Storefront or Dashboard breaks a certified backend, platform rules require **adding probes/bundles**, not weakening Tier 1 — see workspace rules and [COMPATIBILITY.md](COMPATIBILITY.md).
