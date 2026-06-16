# Saleor Test Platform — Data-Independence Refactor Plan

**Date:** 2026-06-15 (Updated: 2026-06-17)
**Goal:** Transform the testing methodology from "replay demo data and compare" to "create data via mutations, query, validate schema shape."

## Current Status: ✅ COMPLETE (refactor) + ✅ VERIFIED (production readiness)

All **17** fixes have been implemented and tested. The platform now:
- Creates required data via mutations before querying (mutation-first)
- Validates response schema shape (field types) instead of data values
- Eliminates dependency on hardcoded Saleor demo data
- Includes enforcement tests to prevent regression
- **Does NOT use `populatedb`** — all entities are created via mutations

## Problem Statement

The current system records golden responses from the Saleor demo database and expects the target backend to reproduce structurally identical responses. This is fundamentally wrong — a compatibility tester should validate that the backend implements the same schema and mutation semantics, not that it has the same data.

## Data Independence (2026-06-17 Update)

### Key Changes

1. **Removed `populatedb` from `cmd_fresh()`** — The test workflow no longer runs `manage.py populatedb`. All entities are created via mutations.

2. **Extended `seed_reference_data()`** — Now creates orders, categories, and warehouses via mutations:
   - `_ensure_order()`: Creates a draft order with line items and completes it
   - `_ensure_category()`: Creates a category via `categoryCreate`
   - `_ensure_warehouse()`: Creates a warehouse via `warehouseCreate`

3. **Added `just record-golden` command** — Easy re-recording against fresh Saleor:
   - `just record-golden` (records all L3 bundles)
   - `just record-golden dashboard` (dashboard only)
   - `just record-golden storefront` (storefront only)

4. **Updated rules** — Added golden recording methodology to `.cursor/rules/saleor-test-platform.mdc`:
   - Never record goldens against `populatedb` instance
   - Data-specific expectations are forbidden in goldens
   - Golden responses are schema-validated, not data-compared
   - Volatile paths are forgiven during comparison

### Workflow

**Before (old approach):**
```
just fresh  # runs populatedb + seed_reference
just baseline  # compares against populatedb data
```

**After (new approach):**
```
just fresh  # runs seed_reference only (no populatedb)
just baseline  # compares against mutation-created data
just record-golden  # re-record goldens if needed
```

### Why This Matters

- **Custom backends** (Go, Node, Rust) don't have Saleor's `populatedb` data
- **Testing should be self-contained** — create data via mutations, query, verify
- **Golden responses are schema templates** — field types, not data values
- **Volatile paths are forgiven** — `.edges`, `.name`, `.amount`, etc.

## Fix Order (dependency-driven)

| # | Issue | Status | Files Changed |
|---|-------|--------|---------------|
| 1 | Mutation-first testing framework | ✅ Done | `services/probe_setup.py` (new), `services/test_runner.py` |
| 2 | Expand fixture coverage | ✅ Done | `services/demo_seed.py` |
| 3 | Schema-based comparison logic | ✅ Done | `services/reference_compare.py`, `services/schema_compare.py` (new) |
| 4 | Data-independent scenario comparison | ✅ Done | `services/reference_compare.py` |
| 5 | Data-independent storefront L3 | ✅ Done | Inherits from schema comparison + storefront session |
| 6 | Robust fixture resolver | ✅ Done | `services/fixture_resolver.py`, `services/reference_seed.py` |
| 7 | L1 success probe comparison fix | ✅ Done | `services/reference_compare.py` |
| 8 | Failure reporting transparency | ✅ Done | `services/ai_report.py`, `services/test_runner.py` |
| 9 | Golden staleness detection | ✅ Done | `services/version_routing.py` |
| 10 | Documentation update | ✅ Done | `docs/COMPATIBILITY.md`, `REFACTOR-PLAN.md` |
| 11 | Fix all Saleor 3.x input types | ✅ Done | `services/probe_setup.py`, `services/demo_seed.py` |
| 12 | Fix Relay ID entity type prefix | ✅ Done | `services/test_runner.py` |
| 13 | Remove orphaned dead code | ✅ Done | `services/demo_seed.py` |
| 14 | Suppress PytestCollectionWarning | ✅ Done | `tests/conftest.py`, `pyproject.toml` |
| 15 | Add missing volatile path fragments | ✅ Done | `services/schema_compare.py` |
| 16 | Wire golden staleness into test flow | ✅ Done | `services/test_runner.py` |
| 17 | Mutation-first enforcement tests | ✅ Done | `tests/test_mutation_first.py` |

## Detailed Fix Descriptions

### Fix 1: Mutation-First Testing Framework

**What:** Create a `ProbeExecutor` that, for each endpoint classified as `success` contract:
1. Generates a setup mutation to create the required entity
2. Executes the setup mutation against the target
3. Extracts the created entity's ID
4. Substitutes the ID into the query
5. Executes the query
6. Validates the response shape (types, not values)

**Why:** This is the foundation. All other fixes depend on the ability to create data dynamically before querying.

### Fix 2: Expand Fixture Coverage

**What:** Extend `demo_seed.py` to create all entity types referenced by L3 bundles:
- Pages with page types
- Attributes and attribute values
- Vouchers
- Gift cards
- Promotions/sales
- Menus and menu items
- Plugins (at least stub)

**Why:** Without this, L3 bundles referencing these entities fail with `data_prerequisite` and are excluded from scoring.

### Fix 3: Schema-Based Comparison Logic

**What:** Change the comparison engine to validate response **schema shape** (field types, nullability, nesting) instead of data values. The golden response becomes a **schema template** (expected types at each path) rather than a literal JSON snapshot.

**Why:** A backend returning `{"name": "Foo"}` should match a golden of `{"name": "Bar"}` — both are `{name: string}`.

### Fix 4: Data-Independent Scenario Comparison

**What:** Scenarios already chain state via `{{context.*}}`. Fix the comparison to validate that each step's response has the correct shape for the **data created in that run**, not the demo data.

**Why:** Step 2's golden expects the demo's product name from step 1. Your product name should be accepted.

### Fix 5: Data-Independent Storefront L3

**What:** Storefront bundles should use dynamic fixture IDs from the current run, and comparison should validate shape not values. The `storefront_session.py` already creates checkout chains — extend this to cover all storefront entity dependencies.

**Why:** Storefront L3 is currently locked to the demo topology.

### Fix 6: Robust Fixture Resolver

**What:** Instead of `first: 1` discovery, query for entities that match expected characteristics (e.g., "find a published product with variants on the channel"). Fall back to creation when no match exists.

**Why:** `first: 1` picks arbitrary entities that may not have the shape the probe expects.

### Fix 7: L1 Success Probe Comparison Fix

**What:** For L1 probes with `success` contract, compare normalized response shape (field types only) instead of normalized hash. Apply the same volatile-path forgiveness currently reserved for L3 bundles.

**Why:** L1 success probes currently fail when the target has different data than the demo.

### Fix 8: Failure Reporting Transparency

**What:** Split the incompatible count into explicit categories in reports:
- `deprecated` (excluded from denominator)
- `data_prerequisite` (excluded from denominator)
- `seed_prerequisite` (excluded from denominator)
- `schema_mismatch` (real failure)
- `shape_drift_data` (data difference, not API bug)

**Why:** Current reporting masks real issues behind "effective score" exclusions.

### Fix 9: Golden Staleness Detection

**What:** Store the Saleor version hash alongside golden data. Add a pre-flight check that compares recorded version against target API version and warns on patch drift.

**Why:** Golden data may drift silently when Saleor releases patches.

### Fix 10: Documentation Update

**What:** Update all docs to reflect the new mutation-first methodology and explain why data-independence matters.

**Why:** The docs currently describe the old "replay demo data" approach.

### Fix 17: Mutation-First Enforcement Tests

**What:** Create tests that verify the mutation-first framework is properly implemented and cannot be accidentally bypassed.

**Tests:**
1. `test_all_success_operations_have_setup_mutations` — ensures every L1 operation that can return data has a setup mutation
2. `test_setup_mutations_have_required_fields` — validates each setup mutation has mutation, variables, extract, category, auth
3. `test_needs_setup_returns_true_for_success_probes` — confirms success probes trigger data creation
4. `test_needs_setup_returns_false_for_error_probes` — verifies error probes don't need data setup
5. `test_setup_mutations_create_entities_not_query_existing` — ensures setup mutations use Create mutations, not queries
6. `test_shop_is_excluded_from_mutation_first` — validates read-only shop query is properly excluded

**Why:** Prevents regression to hardcoded data dependency. These tests run in CI and block merges that break mutation-first testing.

## Summary

The refactoring is **complete**. The platform now:

1. **Creates data dynamically** — L1 success probes execute setup mutations before querying
2. **Validates schema shape** — Response comparison checks field types, not data values
3. **Eliminates demo dependency** — Testing works against any Saleor instance with correct schema
4. **Enforces the pattern** — Tests prevent regression to hardcoded data dependency
5. **Reports accurately** — Failure categories distinguish structural bugs from data differences

**Next steps for production readiness:**
- Re-record golden corpus against freshly seeded Saleor
- Run full E2E test suite
- Deploy to CI/CD pipeline

## Phase 2: Production verification (2026-06-16)

Local verification (no GitHub CI). Run **one** `just baseline` per session; reset `saleor-cache` volume if Saleor login rate-limits after repeated runs.

| Check | Command | Result (2026-06-16) |
|-------|---------|---------------------|
| Unit tests | `just test` | 238 passed, 1 skipped |
| Frontend types | `just check` | 0 errors |
| Golden baseline | `just baseline` | **100%** (856/856) on official Saleor 3.23.7 |
| Full local matrix | `just verify` | Orchestrates unit + check + baseline + e2e |
| E2E API certification | `just test-e2e` | Passed (in-compose `saleor-api:8000`) |

**Fixes landed for verification:** env-driven host ports (`.env.example`), runtime corpus paths on `/app/reference/`, `golden_contract` on L1 endpoints (mutation-first guard), Saleor 3.23.7 health probe (`{ __typename }`), fixture discovery via `channelListings`, auth refresh only when token invalid.

**Remaining baseline gaps:** None after scenario re-record on 2026-06-16 (`just patch-corpus --scenarios …` then `just baseline` → 100%).
