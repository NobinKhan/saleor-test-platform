# Saleor 3.23.7 compatibility — issues for test team

Action items for **saleor-test-platform** maintainers when certifying **Basmalahub Commerce**. Harness fixes belong in the harness repo — not in basmalahub-commerce.

## Scope

| Item | Value |
|------|-------|
| Target API | Saleor 3.23.7 GraphQL at merchant URL (e.g. `http://<host>:8000/graphql/`) |
| Staff login | `merchant@demo.basmalahub.local` / `changeme` (`tokenCreate` — dashboard staff only) |
| Latest report | [`report.md`](report.md) (gitignored locally; export from harness UI) |

## API-side fixes (already in basmalahub-commerce)

These are **not** harness bugs. Do not re-file as API defects:

- **Dashboard product list sort:** `ProductOrderField` includes `DATE`; `products(sortBy: …)` wired to SQL sort
- **Staff metadata:** `updateMetadata` / `deleteMetadata` accept relay global IDs (`User:{pk}` from `me.id`)
- **Product create:** `ProductCreateInput.attributes` exposed for dashboard `productCreate`
- **Catalog slug save:** blank dashboard `slug: ""` falls back to name/title via `resolve_catalog_slug` (fixes `categoryCreate` / `productCreate` with auto-empty slug)
- **Category relay ID:** `category(id: …)` and category mutations accept relay `Category:{pk}` global IDs (fixes post-`categoryCreate` Dashboard refetch)
- **New product variant name:** `productVariantCreate` / `productVariantBulkCreate` default omitted variant `name` to parent product name (Dashboard New Product save)
- **Dashboard session restore:** `externalRefresh` accepts `pluginId: null` and defaults to `mirumee.authentication.openidconnect` (native JWT refresh for `externalRefreshWithUser`)
- **External auth `input` scalar:** `externalRefresh` / `externalObtainAccessTokens` / `externalAuthenticationUrl` / `externalVerify` / `externalLogout` use Saleor's `JSONString` (JSON-encoded string) for `input`, so the Dashboard refresh-token payload parses natively instead of falling through to the webhook path
- **Dashboard `UserDetails` auth:** GraphQL middleware prefers Saleor `authorization-bearer` over stale `Authorization`; `tokenRefresh`/`externalRefresh` access JWT uses `sub = public_id` (same as `tokenCreate`); HTTP compat probes cover login, reload (`externalRefresh` → `UserDetails`), and stale-`Authorization` conflict
- **Dashboard `GridAttributes`:** `AttributeType` enum renamed in SDL to `AttributeTypeEnum` (Saleor 3.23.7 parity); `attributes(filter: { type: $type })` and `attributes(filter: { ids: $ids })` Dashboard paths covered by compat probe
- **Order lines / publish:** `productChannelListingUpdate.updateChannels`; `product(slug: …)` variant loading; `orderLinesCreate` order-channel scope + relay `Order` IDs
- **Checkout / shop parity:** guest checkout token scope; `sitesettings` / countries (see [`docs/SALEOR_GAPS.md`](docs/SALEOR_GAPS.md))

---

## Issues (test team)

### ISSUE-1: Dashboard CLIENT_BUNDLE replays omit live UI paths

- **Status:** ✅ Fixed (harness) — smoke bundles + setup chains added; goldens pending re-record on official Saleor 3.23.7.
- **Symptom:** Harness can report **certified** while Saleor Dashboard 3.23.6 hits schema/validation errors on paths the bundles never exercise.
- **Fix:** Added **7 dashboard success-path smoke bundles** under `reference/client-bundles/dashboard-3.23.6/bundles/smoke-*` that replay the live Dashboard mutation success path (not error contracts) with real fixture-backed input:
  - `productcreate-success` — `productCreate(input: { name, productType, attributes })` with setup chain creating a product type
  - `categorycreate-success` — `categoryCreate(input: { name, slug: "" })` (empty-slug derivation)
  - `categorydetails-aftercreate` — `category(id: <relay>)` after `categoryCreate` (relay refetch) via [`BUNDLE_SETUP`](backend/app/services/bundle_setup.py) chain
  - `productvariantbulkcreate-success` — `productVariantBulkCreate` without `name` (defaults to product) via setup chain
  - `saveonboardingstate-success` — `updateMetadata(id: <me id>, ...)` using `staff_user_id` from fixture resolution
  - `updatemetadata-success` — `updateMetadata` with relay staff user ID
  - `externalrefresh-success` — `externalRefresh(pluginId: null, input: { refreshToken })` after `tokenCreate` via [`BUNDLE_SETUP`](backend/app/services/bundle_setup.py) chain
- **Fixture plumbing:** `staff_user_id` is now resolved once during `resolve_fixtures()` (`me { id }`) and exposed to bundle variables; `categorydetails-aftercreate` and `externalrefresh-success` chains create the prerequisite entities via mutations before replaying the success path (see [`bundle_setup.py`](backend/app/services/bundle_setup.py) and [`fixture_resolver.py`](backend/app/services/fixture_resolver.py)).
- **Examples (fixed in API; harness now replays to catch regressions):**

| Dashboard path | Harness gap | Success-path replay |
|----------------|-------------|---------------------|
| Product list default date sort | `productlist` uses `sort: null` | `sortBy: { field: DATE, direction: DESC }` |
| Staff onboarding `updateMetadata` | `saveonboardingstate` / `updatemetadata` use `placeholder_id` | `id` from `me { id }` (relay `User:{pk}`) |
| Product create with type attributes | `productcreate` uses `input: null` | `productCreate(input: { name, productType, attributes: [...] })` |
| Category/product save with empty slug | bundles may omit `slug: ""` | `categoryCreate(input: { name, slug: "" })` / `productCreate` same shape |
| Post-create category detail refetch | bundles may not query `category(id: relay)` after create | `category(id: <relay id from categoryCreate.category.id>)` |
| New product save (variant step) | bundles may send variant price without `name` | `productVariantBulkCreate(product: <relay>, variants: [{ price, cost, trackInventory }])` without `name` |
| Dashboard session restore | bundles may omit `pluginId` or pass `null` | `externalRefresh(pluginId: null, input: { refreshToken })` after `tokenCreate` |
| Post-login `UserDetails` (`me`) | bundles may not replay full Dashboard fragment after `tokenCreate` | `me { accessibleChannels { stockSettings { allocationStrategy } } userPermissions avatar restrictedAccessToChannels }` |

- **Remaining:** Record goldens for the smoke bundles from official Saleor 3.23.7 (`just fresh && just record-golden dashboard`).
- **API verification:** `crates/api/tests/compat_probes.rs` — `zz_products_sort_by_date_accepts_product_order_field`, `zz_update_metadata_accepts_staff_relay_user_id`, `zz_product_create_accepts_attributes_field`, `zz_category_create_empty_slug_derives_from_name`, `zz_category_query_accepts_relay_id_after_create`, `zz_product_create_empty_slug_derives_from_name`, `zz_product_variant_bulk_create_without_name_defaults_to_product`, `zz_product_variant_create_without_name_defaults_to_product`, `zz_external_refresh_accepts_null_plugin_id`, `zz_external_refresh_malformed_input_returns_no_token`, `zz_me_user_details_dashboard_shape`, `zz_me_user_details_via_authorization_bearer_header`, `zz_me_authorization_bearer_wins_over_stale_authorization`, `zz_me_user_details_after_external_refresh`, `zz_attributes_filter_by_type_via_attribute_type_enum`, `zz_me_invalid_token_returns_graphql_error`.

### ISSUE-2: Missing per-probe latency telemetry

- **Status:** ✅ Fixed (harness) — `operation_name` column + per-operation latency (p50/p95/p99) now in all report exports.
- **Symptom:** `report.md` shows latency variance (many probes >50ms while most are <50ms) but does not break down latency by GraphQL operation name. API team cannot tell which query/mutation (e.g. `products`, `productVariantBulkCreate`, `checkoutCreate`, `orderLinesCreate`) is spiking.
- **Root cause (API side, not harness):** No cache layer exists; per-request channel/tenant access DB round-trip, sync webhooks inline in resolvers (30s timeout), N+1 risk from nested `fetch_all` without DataLoader, and a 10-connection pool shared with background workers.
- **Fix (harness):**
  - Added **`operation_name`** to the `TestResult` model ([`models/__init__.py`](backend/app/models/__init__.py)) with an idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migration ([`db_migrate.py`](backend/app/core/db_migrate.py)).
  - Operation name is extracted from the GraphQL document via `_extract_operation_name()` and propagated through the endpoint dict → result event → `TestResult` row ([`test_runner.py`](backend/app/services/test_runner.py), [`client_bundles.py`](backend/app/services/client_bundles.py), [`sse_manager.py`](backend/app/services/sse_manager.py)).
  - Added **`OperationLatency`** schema and **p99** to `LatencySummary` ([`schemas/__init__.py`](backend/app/schemas/__init__.py)); `_latency_by_operation()` groups response times by operation name and sorts by p95 ([`reports.py`](backend/app/routes/reports.py)).
  - `latency_by_operation` is surfaced on `ReportData` and in all exports: AI report Markdown + JSON ([`ai_report.py`](backend/app/services/ai_report.py)), PDF (top-15 latency table), and CSV (`Operation Name` column).
  - Outliers with p95 > 100ms are flagged `latency_outlier`.
- **API team action once data is available:** Target the named resolvers — add DataLoader for nested catalog fields, cache channel/tenant access scope per request, and tighten sync-webhook timeouts.
- **Why not Valkey:** Caching is not the root cause of the variance; no cache layer exists today. Per-probe data is required first to pick the highest-impact fix.
