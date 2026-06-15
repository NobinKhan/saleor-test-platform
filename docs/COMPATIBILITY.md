# Saleor Compatibility Standard

This platform verifies that a GraphQL backend is **fully compatible with official Saleor** — same queries, mutations, schema, inputs, and **SGRC** response semantics.

See [CLIENT-CONTRACT.md](CLIENT-CONTRACT.md) for the cross-language response contract (Python, Go, Node, Rust).

## Certification criteria

A backend is **certified Saleor-compatible** only when **all** of the following pass:

| Gate | Requirement |
|------|-------------|
| Schema gate | Every operation in the reference corpus exists on the target schema |
| Compatibility score | **100%** — every probe/bundle in scope passes SGRC match |
| Effective score | **100%** — excludes deprecated + data-prerequisite + seed-prerequisite probes from denominator |
| Tier 1 | Message + data semantics (errors); normalized shape (success) |
| Tier 2 | When `SGRC_TIER2_GATE=true`: zero `parity_gap` / `tier2_fail` — path + codes where golden have them |
| Input parity | L1 replays exact `input_sent`; L3 replays exact dashboard documents + fixtures |
| Dynamic probes | Runtime-generated values must echo in response (anti-static-response) |
| Version gate | Target version must match corpus version (major/minor hard fail; patch drift optional) |

Tier 1 is **not** byte-identical JSON to Python Saleor. Stack traces, locations, and cost extensions are never required.

Partial scores are **not** certified. Harness gaps are **platform failures**.

## Migration: Tier 2 hard gate

During migration, `SGRC_TIER2_GATE` was enabled after official Saleor passed `just baseline`.

## Golden baseline

Before testing other backends, official Saleor must pass:

```bash
just up
just baseline
```

This chains corpus integrity (387 L1 + 415 L3 dashboard + 31 L3 storefront recorded, schema gate) and full replay (`full+scenarios`, Tier 2, 100% on **856** scored endpoints).

L3 golden capture requires seeded fixture data — see [REFERENCE-SEED.md](REFERENCE-SEED.md). `just fresh` runs `populatedb` and `just seed-reference` automatically.

## How testing works

1. **Pre-flight validation** — `POST /api/runs/validate` checks API reachability, version match, and fixture entities.
2. **L1 reference corpus** — synthetic introspection probes (`reference/corpora/saleor-{VERSION}/`).
3. **L3 dashboard bundles** — real Dashboard GraphQL (`reference/client-bundles/dashboard-{VERSION}/`).
4. **Dynamic probes** — runtime-generated inputs with echo/structural/semantic validation (anti-static-response).
5. **Compatibility mode** — replays golden inputs; compares SGRC Tier 1 (+ Tier 2 when gate on).
6. **Schema gate** — introspects target; verifies corpus operations exist.
7. **Deprecated auto-exclusion** — bundles/ops referencing deprecated Saleor types are excluded from scoring.

**Full-system scope** (`full+scenarios`) = 387 L1 + **415** L3 dashboard + **31** L3 storefront + **15** scenario steps + **3** variants + **5** dynamic probes = **856 scored endpoints**. **11** deprecated dashboard bundles were removed from the corpus (deprecated Sale API, `exportProducts`, Apollo `@client` fields, etc.). See [COVERAGE-GAPS.md](COVERAGE-GAPS.md).

Reports include `failure_category`, `effective_score`, `not_counted_note`, and `excluded_l3_bundles` so AI agents know deprecated and seed-dependent items are never counted toward compatibility %. See [COMPAT-TEST-IMPROVEMENT-REPORT.md](COMPAT-TEST-IMPROVEMENT-REPORT.md) for external backend seed guidance.

## Recording and patching

**L1 corpus:**

```bash
just corpus-diff
just patch-corpus --apply-diff
just verify-corpus
just self-check --min-compat 100
```

**L3 dashboard bundles** (same commands — no separate just recipes):

```bash
just patch-corpus --sync-client              # import from reference/vendor/
just seed-reference                          # fixture IDs for bundle variables
just patch-corpus --client-bundles all       # record golden on official Saleor
just baseline
```

L3 **schema gate**: every recorded bundle's root query/mutation field must exist on the target schema (checked without executing bundles).

## Testing a custom backend

```bash
just up-harness
just register
# UI: start a run (full-system scope is automatic)
```

Point the UI at your backend — every run uses **`full+scenarios`**. Seed fixture data on the target DB when testing L3 (see [REFERENCE-SEED.md](REFERENCE-SEED.md)).

## Local verification (no CI)

| Check | Command |
|-------|---------|
| Golden baseline | `just baseline` |
| Build + start harness | `just up-harness` |
| Corpus integrity | `just verify-corpus` |
| Backend unit tests | `just test` |

## Coverage gaps (out of scope today)

What passing certification does **not** yet guarantee: Storefront L3 bundles, customer-session JWT replay, multi-step scenario chains, async webhooks/workers, and live payment plugins. Prioritized gap list and follow-up work: [COVERAGE-GAPS.md](COVERAGE-GAPS.md).
