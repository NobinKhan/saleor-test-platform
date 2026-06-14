---
name: Testing System Hardening
overview: "Second verification (2026-06-13): ~85% complete. Major wiring landed (+95 tests, 179 total). Remaining: 1 failing test, 3 runtime bugs, corpus goldens not recorded, sale bundles on disk, README, and baseline proof."
todos:
  - id: fix-runtime-bugs
    content: "P0: Fix counts NameError on version-gate early return; probe_tiers SCENARIO_STEP + split mutating L3 from parallel tier 0"
    status: completed
  - id: fix-failing-test-baseline
    content: "P0: Update test_runner_scope L3 count 415 vs 417; align just baseline --min-client-bundles and README probe counts"
    status: completed
  - id: record-goldens-prune-corpus
    content: "P1: Run patch-corpus --scenarios product-lifecycle --variants productCreate against Saleor; remove saletranslations/saletranslationdetails from disk"
    status: completed
  - id: missing-golden-fail
    content: "P1: missing_golden → fail (not warn) in compatibility mode; remove duplicate return in _classify_failure_category"
    status: completed
  - id: docs-commit-baseline
    content: "P1: Update README + REFERENCE-SEED; fix check-corpus-version to call version gate; commit changes; run just baseline"
    status: completed
isProject: false
---

# Testing System Hardening — Second Verification Report

**Verified:** 2026-06-13 after second implementation pass (still uncommitted on `main`).

---

## Overall verdict

**Substantially improved — not done.** The second pass wired most scaffolded code and added **95 new tests** (179 total, was 84). One test fails. Three runtime bugs could cause crashes or incorrect probe ordering. Scenario/variant goldens were **not recorded** despite new `patch-corpus` flags.

| Area | First pass | Second pass |
|------|------------|-------------|
| Core wiring | ~40% | **~85%** |
| Unit tests | 84 | **179** (1 failing) |
| Corpus goldens | 0/9 | **0/9** (still) |
| Git commit | None | **Still none** |
| `just baseline` | Not verified | **Not verified** |

---

## What is now done (verified in code)

### P0 items — mostly complete

| Item | Status | Evidence |
|------|--------|----------|
| DB migration `failure_category` | **Done** | [`db_migrate.py:20`](backend/app/core/db_migrate.py) |
| Runtime fixture resolver wired | **Done** | [`test_runner.py:657-673`](backend/app/services/test_runner.py) calls `resolve_fixtures()` with correct keys |
| Dynamic probe echo + productType ID | **Done** | [`reference/dynamic/*.json`](reference/dynamic/); `resolve_dynamic_probe_support()`; `generated_values` on endpoints |
| `version_hard_gate_check` wired | **Done** | Run start + [`validate_preflight`](backend/app/services/fixture_resolver.py) |
| `effective_score` for certification | **Done** | [`schema_gate.compute_certified`](backend/app/services/schema_gate.py) + reports |
| `_classify_failure_category` fixed | **Mostly** | Scans document not bundle_id; duplicate dead `return` at line 1302 |
| `input_binding` wired | **Done** | Post-SGRC binding in [`test_runner.py:1107-1149`](backend/app/services/test_runner.py) |
| Parallel probe tiers | **Partial** | Wired but **two bugs** (see below) |
| Deprecated scanner | **Done** | L3 count 415 (was 417; 2 sale bundles excluded at runtime) |
| L1 `saleBulkDelete` removed | **Done** | Probe file deleted |
| Frontend validate | **Done** | [`run/new/+page.svelte`](frontend/src/routes/run/new/+page.svelte) calls `/api/tests/validate` |
| Frontend reporting | **Done** | Effective score, deprecated/data-prereq counts, top field diffs |
| Dynamic probes JSON | **Done** | 5 probes in [`reference/dynamic/`](reference/dynamic/) |
| patch-corpus flags | **Done** | `--scenarios`, `--variants` + [`scenario_variant_record.py`](backend/app/services/scenario_variant_record.py) |
| New tests | **Done** | `test_deprecated_scanner`, `test_fixture_resolver`, `test_dynamic_corpus`, `test_input_binding`, `test_probe_tiers`, `test_certification_api` |
| `just check-corpus-version` | **Partial** | Recipe exists; only runs `verify_corpus`, not version hard gate |

---

## Remaining bugs (must fix)

### Bug 1 — `NameError` on version gate abort

When version hard gate fails, early return references `counts` **before it is defined** (line 609 vs 641):

```python
# test_runner.py ~600-613 — counts not defined yet
"status_counts": counts,  # NameError
```

**Fix:** Use `{"pass": 0, "fail": 0, "warn": 0, "skip": 0}` inline or initialize `counts` before gate check.

### Bug 2 — Scenario steps not in Tier 2

[`probe_tiers.py`](backend/app/services/probe_tiers.py) checks `SCENARIO_KIND` / `SCENARIO` but actual kind is **`SCENARIO_STEP`** ([`scenario_corpus.py:13`](backend/app/services/scenario_corpus.py)). Scenarios fall through to Tier 1, interleaved with other mutations instead of strict ordered execution.

**Fix:** Add `SCENARIO_STEP` to tier-2 check.

### Bug 3 — Mutating L3 bundles run in parallel Tier 0

All `CLIENT_BUNDLE` endpoints are Tier 0 with `PROBE_CONCURRENCY=4`. Many dashboard bundles are **mutations** (e.g. `productvariantsetdefault`). Parallel mutation L3 probes can race on shared DB state.

**Fix:** Classify L3 by operation kind (parse document for `mutation` vs `query`) or use bundle metadata; mutations → Tier 1 sequential.

### Bug 4 — Failing unit test

```
FAILED tests/test_runner_scope.py::test_certification_l3_set_independent_of_extra_target_fields
```

Test asserts `len(l3_golden) == 417`; runtime deprecated exclusion yields **415**. Test and [`just baseline --min-client-bundles 410`](justfile) need updating to reflect certified L3 count (415) vs on-disk count (417).

---

## Corpus gaps (still open)

| Item | Expected | Actual |
|------|----------|--------|
| Scenario step goldens | 6/6 | **0/6** — no `golden_response` in any step JSON |
| Variant goldens | 3/3 | **0/3** — not in matrix JSON |
| saletranslations / saletranslationdetails on disk | Removed | **Still present** — runtime-excluded only |
| `missing_golden` in cert mode | fail | **warn** ([`test_runner.py:1094`](backend/app/services/test_runner.py)) |

**Required actions (needs running Saleor):**

```bash
just up
just patch-corpus --scenarios product-lifecycle \
  --variants productCreate \
  --url http://saleor-api:8000/graphql/ \
  --email admin@example.com --password admin123456
just patch-corpus --remove saletranslations saletranslationdetails
just verify-corpus
just baseline
```

---

## Documentation gaps

| Doc | Status |
|-----|--------|
| [`docs/DYNAMIC-PROBES.md`](docs/DYNAMIC-PROBES.md) | Done |
| [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) | Updated |
| [`docs/COVERAGE-GAPS.md`](docs/COVERAGE-GAPS.md) | Updated (claims some items done before goldens recorded) |
| [`README.md`](README.md) | **Not updated** — no validate, effective score, dynamic probes |
| [`docs/REFERENCE-SEED.md`](docs/REFERENCE-SEED.md) | **Not updated** — no runtime resolver section |

---

## Test results

```
179 passed, 1 failed (test_runner_scope L3 count)
```

Anti-static tests exist in `test_dynamic_corpus.py` and `test_input_binding.py`. No end-to-end mock-server integration test yet (optional P2).

---

## Sprint plan (remaining ~1–2 days)

### Step 1 — Fix bugs (same day)

1. Initialize `counts` before version gate OR inline dict on early return
2. Fix `probe_tiers`: `SCENARIO_STEP` → tier 2; mutating L3 → tier 1
3. Remove duplicate `return "real_bug"` in `_classify_failure_category`
4. Update `test_runner_scope.py`: expect 415 certified L3; document 417 on-disk vs 415 scored
5. `missing_golden` → `fail` in compatibility mode (unless `SGRC_ALLOW_ASSERTION_ONLY`)

### Step 2 — Corpus + baseline (needs Saleor stack)

1. Record scenario + variant goldens via new patch-corpus flags
2. Remove deprecated sale* bundles from disk + update manifests
3. Run `just baseline` — must PASS
4. Update README probe counts (388 L1, 415 certified L3, +5 dynamic, etc.)

### Step 3 — Ship

1. Fix `check-corpus-version` to include `version_hard_gate_check` or rename recipe
2. Update REFERENCE-SEED with runtime resolver workflow
3. Commit: `feat(harness): harden certification with dynamic probes and runtime fixtures`

---

## Verification checklist (updated)

| Check | Status |
|-------|--------|
| `just test` all pass | **FAIL** — 1 test |
| `failure_category` DB column | **PASS** |
| Runtime fixtures in runner | **PASS** |
| Dynamic echo validation | **PASS** (code review) |
| Parallel tiers safe | **FAIL** — L3 mutation race + scenario tier |
| Version gate abort | **FAIL** — NameError |
| Scenario goldens recorded | **FAIL** — 0/6 |
| sale* pruned from disk | **FAIL** |
| Frontend validate + effective score | **PASS** |
| `just baseline` | **NOT RUN** |
| Git commit | **NOT DONE** |

---

## Tester report ([report.md](report.md)) — current status

| # | Suggestion | Now |
|---|------------|-----|
| 1 | Deprecated auto-exclusion | **Runtime yes**; disk prune pending |
| 2 | Dynamic seed | **Done** — runtime resolver wired |
| 3 | Scenario goldens | **Not recorded** — tooling exists |
| 4 | Structured reporting | **Done** — backend + UI |
| 5 | Pre-flight validate | **Done** — API + UI |
| 6 | Version pinning gate | **Done** — wired (with NameError bug on abort) |
| 7 | Parallel tiers | **Partial** — wired but unsafe for L3 mutations |
| 8 | Field diff | **Done** — backend + top diffs UI |

**Basmalahub 99.4% → 100% effective:** Should work once sale bundles are pruned from denominator and fixture resolver runs — **needs live verification**.
