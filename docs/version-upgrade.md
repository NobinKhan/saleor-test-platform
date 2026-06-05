# Saleor reference version upgrade playbook

The test platform uses **three independent version layers**. Do not conflate them in config or reports.

| Layer | Env / artifact | What it is |
|-------|----------------|------------|
| **Catalog** | `REFERENCE_BASELINE_VERSION` | Operation *names* from saleor-dashboard (static lists in `test_runner.py`) |
| **Golden corpus** | `GOLDEN_CORPUS_VERSION`, `reference/corpora/saleor-{version}/` | Recorded GraphQL request/response pairs from official Saleor |
| **Docker pin** | `docker-compose.yml` `saleor-api` image tag | Official Saleor used to *produce* golden snapshots |

## When to upgrade

| Release type | Example | Action |
|--------------|---------|--------|
| **Patch** | 3.23.7 → 3.23.8 | Optional re-record; normalization usually enough; report shows patch drift warning |
| **Minor** | 3.23.x → 3.24.0 | **Required:** new corpus, catalog refresh, Docker pin |
| **Major** | 3.x → 4.0.0 | New baseline; do not reuse 3.x golden |

## Standard workflow

```bash
just upgrade-reference 3.24.0
```

This runs:

1. Reminds you to pin `ghcr.io/saleor/saleor:3.24.0` in `docker-compose.yml`
2. `just fresh` — reset Saleor DB and create admin
3. `just record-reference-docker` — writes `reference/corpora/saleor-3.24.0/`
4. Updates `reference/corpora/registry.json`
5. `just golden-gate --min-probes 400 --version 3.24.0`

Then update env:

```env
GOLDEN_CORPUS_VERSION=3.24.0
REFERENCE_BASELINE_VERSION=3.24.x   # dashboard catalog tag when available
```

Commit the new corpus folder and registry in a reviewable PR.

## Multi-version support

Keep corpora side by side:

```
reference/corpora/
  registry.json
  saleor-3.23.7/
  saleor-3.24.0/
  _archive/          # deprecated corpora
```

At test time, `resolve_corpus_version()` picks:

1. Exact match for target `shop.version`
2. Same major.minor (nearest patch)
3. `GOLDEN_CORPUS_VERSION` default

The report **Compatibility context** card shows which corpus was actually used and an upgrade hint when versions diverge.

## Pin rule

Never use floating tags (`:3.23`, `:latest`) for golden capture. Always pin an exact GitHub release tag (`:3.23.7`, `:3.24.0`).

## Certifying custom backends

- Certify against **one Saleor version at a time** (e.g. "3.23.7 compatible")
- **Compatibility score** = golden behavioral match % (separate from pass rate)
- Target: ≥ 95% compatibility + empty schema SDL diff for that version
- Test your custom backend against official golden, not LAN Docker vs Docker noise
