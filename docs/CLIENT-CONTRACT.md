# Saleor GraphQL Response Contract (SGRC)

Cross-system contract every backend we certify must follow — Python, Go, Node, Rust, etc.

The golden corpus is **recorded from official Python Saleor** but certification compares **semantic client contract**, not byte-identical JSON or Python stack traces.

## Sources

| Source | Relevance |
|--------|-----------|
| [GraphQL spec §7](https://graphql.org/learn/response/) | `errors[].message` required; `path`/`locations`/`extensions` optional |
| GraphQL.js | Execution errors should include `path`; never rely on stack traces |
| Saleor Python | Adds `extensions.exception.stacktrace` — **debug only, never SGRC** |
| Saleor Dashboard / Apollo | Reads `message`, partial `data`, often `path` and error codes |

## Tiers

### Tier 1 — Semantic match (required)

| Probe class | Required | Never required |
|-------------|----------|----------------|
| **Error** (`not_found`, `auth_error`, `graphql_error`, `business_error`) | HTTP 200; `errors[0].message` matches golden pattern; `data.<rootField>` null or mutation error payload | `stacktrace`, `extensions.exception` body, `extensions.cost`, `locations` |
| **Success** | Normalized `data` shape (IDs/timestamps normalized) | `extensions.cost`, `__typename` |

### Tier 2 — Client parity (informational + hard gate for client codes)

When `SGRC_TIER2_GATE=true` (default after official Saleor validates):

- `errors[].path` — **informational** (`parity_gap`); Go/Rust backends often omit it
- `extensions.code` (Saleor/Dashboard codes) — **required** when golden records a non-Python code
- `extensions.exception.code` = `GraphQLError` — **never required** (Python debug)

When the gate is off (migration period), gaps appear as `parity_gap` — informational only.

### Tier 3 — Python debug (never required)

Recorded in golden for reference only: `locations`, full `stacktrace`, query cost extensions.

## Expand, never weaken

If Saleor Dashboard or Storefront works against official Saleor but breaks against a certified backend:

1. Reproduce with the frontend's exact GraphQL document
2. Add or patch an L1 probe or **L3 dashboard bundle**
3. Never lower Tier 1 to make a backend pass

## Incremental corpus updates

On Saleor patch releases, patch only changed operations — see [version-upgrade.md](version-upgrade.md):

```bash
just corpus-diff
just patch-corpus --apply-diff
just patch-corpus --remove deprecatedOp
```

## L3 dashboard bundles

Real Saleor Dashboard GraphQL documents live at `reference/client-bundles/dashboard-{VERSION}/`. Source is vendored at `reference/vendor/saleor-dashboard-{VERSION}/` (TypeScript `gql` templates). **No stubs.**

```bash
just patch-corpus --sync-client
just patch-corpus --client-bundles all
just baseline
```

Test scopes: `client-dashboard` (L3 only), `full+client` (L1 + L3). L3 schema gate verifies bundle root fields exist on target schema without executing documents. L3 replays require fixture IDs from [REFERENCE-SEED.md](REFERENCE-SEED.md).

## Coverage layers

| Layer | Description |
|-------|-------------|
| L1 | Introspection corpus (**388** probes for 3.23.7 after deprecated-op prune) |
| L2 | Dashboard catalog (static op lists in `test_runner.py`) |
| L3 | Dashboard query bundles (real documents from vendor + fixtures + golden) |
| L4 | SGRC Tier 2 parity (hard gate when enabled) |

See [COMPATIBILITY.md](COMPATIBILITY.md) for certification criteria.
