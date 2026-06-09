# Corpus maintenance (incremental only)

The harness records golden inputs once from official Saleor. Day-to-day updates are **incremental** — never re-record the full corpus unless you explicitly run a version upgrade.

**Do not add new `just` recipes.** Use the existing commands with script flags.

## Workflow

```bash
just corpus-diff                    # diff live Saleor vs on-disk L1 + L3 (dashboard + storefront)
just patch-corpus --apply-diff      # add new ops, remove deprecated, sync changed bundles
just baseline                       # prove official Saleor still 100%
```

## What `corpus-diff` detects

| Layer | Added | Removed | Changed |
|-------|-------|---------|---------|
| **L1** | New schema query/mutation | Deprecated op | `input_hash` drift |
| **L3 dashboard** | New vendor bundle | Removed bundle | `document_hash` drift |
| **L3 storefront** | New vendor bundle | Removed bundle | `document_hash` drift |

Reports are written to:

- `reference/corpora/saleor-{VERSION}/last_corpus_diff.json`
- `reference/client-bundles/dashboard-{VERSION}/last_corpus_diff.json`
- `reference/client-bundles/storefront-{VERSION}/last_corpus_diff.json`

## Common commands (flags on existing recipes)

```bash
# Import client GraphQL from vendor trees (dashboard + storefront)
just patch-corpus --sync-client

# Record golden on official Saleor
just patch-corpus --client-bundles all              # dashboard + storefront
just patch-corpus --client-bundles dashboard:all    # dashboard only
just patch-corpus --client-bundles storefront:all   # storefront only

# Patch specific L1 operations
just patch-corpus --ops productCreate,checkoutCreate

# Remove deprecated op or bundle
just patch-corpus --remove oldMutation__MUTATION
just patch-corpus --remove bundle-id

# Seed fixtures (dashboard + storefront checkout keys)
just seed-reference
```

## Full re-record (rare)

Only on explicit Saleor version bump:

```bash
bash scripts/upgrade-reference.sh 3.24.0
```

Default maintenance is **incremental patch**, not full re-record.

## Certification scopes

| Scope | Contents |
|-------|----------|
| `full+client` | L1 (388) + L3 dashboard (certified subset) |
| `full+client+storefront` | L1 + L3 dashboard + L3 storefront |
| `scenarios` | L4 multi-step flows (`reference/scenarios/`) |
| `variants` | Input variant matrix (`reference/variants/`) |

See [COMPATIBILITY.md](COMPATIBILITY.md) and [COVERAGE-GAPS.md](COVERAGE-GAPS.md).
