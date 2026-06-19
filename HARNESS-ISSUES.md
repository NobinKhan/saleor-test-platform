# Saleor 3.23.7 compatibility harness — issues for test team

Action items for **saleor-test-platform** maintainers when certifying **Basmalahub Commerce**. Fixes belong in the harness repo — not in basmalahub-commerce.

## Scope

| Item | Value |
|------|-------|
| Target API | Saleor 3.23.7 GraphQL at merchant URL (e.g. `http://<host>:8000/graphql/`) |
| Staff login | `merchant@demo.basmalahub.local` / `changeme` (`tokenCreate` — dashboard staff only) |
| Latest report | [`report.md`](report.md) (gitignored locally; export from harness UI) |

## API-side fixes (already in basmalahub-commerce)

These are **not** harness bugs. Do not re-file as API defects:

- `productChannelListingUpdate` implements Saleor `updateChannels` bulk input (`channelId`, `isPublished`, `addVariants` / `removeVariants`)
- `product(slug: …)` loads variants using resolved `public_id` (slug query no longer returns empty `variants`)
- `orderLinesCreate` resolves the **order's channel** (not staff default), accepts relay `Order` global IDs, validates PCL publish + VCL on that channel
- Guest customer context for L1 validation probes; Saleor token-possession checkout scope; `sitesettings` / countries parity (see [`docs/SALEOR_GAPS.md`](docs/SALEOR_GAPS.md))

---

## Resolved (harness)

### ISSUE-1: `sf-accountupdate` requires customer access JWT — **FIXED**

- Customer probes use `TestRunner._customer_token` only (`_auth_headers()` for `auth_context=customer`).
- `ensure_customer_auth()` in [`saleor_auth.py`](backend/app/services/saleor_auth.py) provisions JWT via `accountRegister.sessionToken` or per-run fallback email.
- Staff `tokenCreate` is never sent on customer-success storefront bundles.

### ISSUE-2: `saleBulkDelete` legacy Sale API in schema gate — **FIXED**

- `saleBulkDelete` is in [`deprecated_scanner.py`](backend/app/services/deprecated_scanner.py) `DEPRECATED_MUTATIONS`.
- [`schema_gate_diff()`](backend/app/services/introspection.py) filters deprecated ops before computing `missing_mutations`.
- No `saleBulkDelete` L1 probe remains in the 3.23.7 corpus manifest.
- **If you still see this:** rebuild `harness-backend` — reference Python is baked at image build time.

### ISSUE-4: Customer JWT prerequisites (5 skipped probes) — **FIXED**

- `resolve_fixtures()` provisions customer JWT during runtime seed; per-run fallback `harness-customer-{runId}@example.com` when staff delete fails.
- `customer_delete_incompatible` warning logged when Basmalahub rejects relay IDs from `customers` query (API defect, not harness skip).
- Expect **0** `auth_prerequisite` skips on customer bundles after rebuild.

---

## Open / recently fixed (verify on next run)

### ISSUE-3: Runtime seed skips publish repair (`order-lifecycle/02`) — **FIXED in harness**

**Symptom:** `orderLinesCreate` returns `PRODUCT_NOT_PUBLISHED`; `order-lifecycle/02_order_line_create` assertion fails.

**Harness fix ( [`reference_seed.py`](backend/app/services/reference_seed.py) ):**

- `_ensure_fixture_variant_purchasable()` — idempotent publish + VCL + stock repair
- No blind early-return when capture already has product/variant IDs
- Publish when channel listing missing **or** `isPublished` is false
- `productVariantCreate` includes `name: "Harness Reference Variant"` on all paths

**Verify:** Rebuild `harness-backend`, run certification; `order-lifecycle/02_order_line_create` should be `pass | match | success`.

### ISSUE-5: Compatibility score hides scenario assertion failures — **FIXED in harness**

- `assertion_fail` rows now count in the compatibility denominator ([`ai_report.py`](backend/app/services/ai_report.py), [`reports.py`](backend/app/routes/reports.py)).
- Executive summary includes **Scenario assertion failures: N**.
- `PRODUCT_NOT_PUBLISHED` (and similar seed codes) on scenario assertions classify as `seed_prerequisite`, not `assertion_fail`.

**Verify:** A failing `order-lifecycle/02` before seed fix should no longer show 100% compatibility when assertion failures remain.

---

## Basmalahub API defect (not harness)

**`customerDelete` relay ID rejection:** When `customers` returns `id: VXNlcjoy` but `customerDelete` responds `Invalid ID: … Expected: User.`, that is a **target API defect** vs Saleor 3.23.x. Harness logs `customer_delete_incompatible` and uses per-run customer email fallback — not SQL delete.

**Basmalahub fix:** Accept User relay IDs from the `customers` query on `customerDelete` / `customerUpdate`.

---

## Failure classification note

- Guest/staff Bearer on customer-only **success** mutations → `auth_prerequisite` or `data_prerequisite`, not `real_bug`.
- `PRODUCT_NOT_PUBLISHED` on scenario steps after seed → `seed_prerequisite` when fixtures were not published on the order channel.
