# Saleor reference version upgrade playbook

**Only upgrade when explicitly requested.** The current reference pin is **3.23.7** (see `docker-compose.yml` and `GOLDEN_CORPUS_VERSION`).

The test platform uses **three independent version layers**. Do not conflate them in config or reports.

| Layer | Env / artifact | What it is |
|-------|----------------|------------|
| **Catalog** | `REFERENCE_BASELINE_VERSION` | Operation *names* from saleor-dashboard (static lists in `test_runner.py`) |
| **Reference corpus** | `GOLDEN_CORPUS_VERSION`, `reference/corpora/saleor-{version}/` | Recorded GraphQL request/response pairs from official Saleor |
| **Docker pin** | `docker-compose.yml` `saleor-api` image tag | Official Saleor used to *produce* reference snapshots |

Certification uses **SGRC Tier 1** (see [CLIENT-CONTRACT.md](CLIENT-CONTRACT.md)) — semantic message + data match, not byte-identical JSON to Python Saleor.

## When to upgrade

| Saleor change | Action |
|---------------|--------|
| **Patch** (3.23.7 → 3.23.8) | `just corpus-diff` → `just patch-corpus --apply-diff` → `just baseline` |
| **Op deprecated/removed** | `just patch-corpus --remove opName` |
| **Op added/changed** | Patch that op only: `just patch-corpus --ops checkout,productCreate` |
| **Minor/major** (user request) | Bump Docker pin + `bash scripts/upgrade-reference.sh {VERSION}` |

Full corpus re-record (`just record-reference`) is only for **user-requested major bumps** or when incremental patch cannot reconcile drift.

## Incremental patch workflow (default)

```bash
just corpus-diff
just patch-corpus --apply-diff
just seed-reference
just patch-corpus --client-bundles all
just baseline
```

Selective re-record:

```bash
just patch-corpus --ops checkout,productCreate --replace
```

Migrate semantic profiles after contract changes (rare):

```bash
docker compose exec harness-backend python -m app.scripts.migrate_semantic_profiles --version 3.23.7
```

## L3 dashboard bundle updates

When saleor-dashboard tag changes (`REFERENCE_BASELINE_VERSION`):

1. Update `reference/vendor/saleor-dashboard-{TAG}/` from upstream.
2. Run the unified corpus workflow:

```bash
just patch-corpus --sync-client
just corpus-diff
just patch-corpus --apply-diff
just patch-corpus --client-bundles all
just baseline
```

`SGRC_TIER2_GATE=true` is enabled in `docker-compose.yml` after baseline passes on official Saleor.

## Full upgrade (user-requested minor/major)

```bash
bash scripts/upgrade-reference.sh 3.24.0
```

This runs:

1. Reminds you to pin `ghcr.io/saleor/saleor:3.24.0` in `docker-compose.yml`
2. `just fresh` — reset Saleor DB and create admin
3. `just corpus-diff` — compare schema against existing corpus
4. `just patch-corpus --apply-diff` — record only changed ops (or full `just record-reference` if major)
5. Migrates semantic profiles for the new version
6. `just verify-corpus --min-probes 400 --version 3.24.0`
7. `just baseline`

Then update env:

```env
GOLDEN_CORPUS_VERSION=3.24.0
REFERENCE_BASELINE_VERSION=3.24.x   # dashboard catalog tag when available
```

**Delete** the old corpus folder — never archive it.

Commit the new `reference/corpora/saleor-{VERSION}/` and updated `registry.json`.

## Single active corpus

Only one reference corpus exists at a time:

```
reference/corpora/
  registry.json
  saleor-3.23.7/    # current active version
    manifest.json   # includes operations_index (manifest v2)
    probes/
    last_corpus_diff.json
```

When upgrading, delete the previous `saleor-{old}/` directory entirely.

## Pin rule

Never use floating tags (`:3.23`, `:latest`) for reference capture. Always pin an exact release tag (`:3.23.7`, `:3.24.0`).

## Certifying custom backends

- Certify against **one Saleor version at a time** (e.g. "3.23.7 compatible")
- **Compatibility score** = SGRC Tier 1 semantic match on reference input replay
- **Schema gate** + **Certified** badge = schema gate pass AND compatibility **100%**
- Default test mode is `compatibility` — replays exact reference `input_sent` per endpoint
- Run `just baseline` on official Saleor before testing external backends
- Test custom backends on a fresh DB with staff credentials; scope **`full+client`**
- Go/Node/Rust backends are first-class — never require Python `stacktrace` or `locations`

See [COMPATIBILITY.md](COMPATIBILITY.md) and [CLIENT-CONTRACT.md](CLIENT-CONTRACT.md) for the full standard.
