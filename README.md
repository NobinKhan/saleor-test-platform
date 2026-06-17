# Saleor Test Platform

GraphQL compatibility test harness for Saleor APIs: replay official Saleor inputs, compare response contracts, and certify **100% compatibility**.

Everything runs from **one** [`docker-compose.yml`](docker-compose.yml) — no `saleor-platform` clone.

**Reference Saleor version:** `3.23.7` (upgrade only when explicitly requested — see [docs/version-upgrade.md](docs/version-upgrade.md)).

## Architecture

| Service | Port | Profile | Image |
|---------|------|---------|-------|
| Saleor GraphQL (`saleor-api`) | 8000 | `saleor` | Official `ghcr.io/saleor/saleor:3.23.7` |
| Saleor DB (`saleor-db`) | — | `saleor` | Chainguard Postgres |
| Harness UI (`harness-frontend`) | 5999 | `harness` | Bun on `node:20-slim` |
| Harness API (`harness-backend`) | 5998 | `harness` | Chainguard Python |
| Harness DB (`harness-db`) | 5997 | `harness` | Chainguard Postgres |

The **harness** stack (backend + DB) uses Chainguard images with no host bind mounts for reference data — corpus is baked into the image and stored in the `harness_reference` named volume. Saleor DB also uses Chainguard Postgres (with a small init SQL mount for replica user setup).

```text
Browser → harness-frontend:5999 → harness-backend:5998 → target Saleor GraphQL
```

## Quick start

Copy [`.env.example`](.env.example) to `.env` when default ports conflict (e.g. `SALEOR_HOST_PORT=18000`).

```bash
just up
just baseline   # prove official Saleor matches golden reference (must PASS)
# Open http://localhost:5999/login
#   Harness UI: test@example.com / testpass123
#   Saleor API (test runs): admin@example.com / admin123456
```

After first install or empty Saleor DB:

```bash
just fresh      # wipes volumes, migrates Saleor, creates admin@example.com / admin123456
just baseline   # re-verify golden baseline
```

## Golden workflow (maintainers)

Re-record L3 and scenario goldens on **mutation-first** harness topology (no `populatedb`):

```bash
just fresh
just record-golden all          # L3 dashboard + storefront
just record-scenarios           # product, checkout, order lifecycles
just build-harness              # bake ./reference/ into harness image
just fresh && just baseline     # must pass 100% (856/856)
```

`just record-golden` and `just record-scenarios` export JSON to `./reference/` automatically. Commit corpus changes, then `just import-reference` on other machines.

Golden literal lint is **blocking** by default (`GOLDEN_LITERAL_LINT_BLOCKING=true` in compose / `.env.example`).

## Commands

| Command | Description |
|---------|-------------|
| `just up` | Saleor + harness (full local stack) |
| `just up-harness` | Harness only — rebuild images, then start |
| `just up-harness-fast` | Harness only — start without rebuild (preferred when images are current) |
| `just down` | Stop all services |
| `just test` | Backend unit tests (in harness container, RAM-safe) |
| `just check` | Frontend type check (capped Node heap) |
| `just build-harness` | Rebuild harness-backend then harness-frontend (serial) |
| `just fresh` | Reset DB volumes + Saleor migrate + reference seed (no populatedb) |
| `just seed-reference` | Seed L3 fixture IDs (products, orders, customers, …) on official Saleor |
| `just register` | Create harness user `test@example.com` |
| `just baseline` | Golden proof: corpus integrity + 100% replay (L1 + L3 + dynamic, Tier 2) |
| `just verify` | Full local matrix: unit + types + baseline + e2e (`--skip-e2e` optional) |
| `just verify-corpus` | Check reference corpus on disk (L1 + L3) |
| `just check-corpus-version` | Corpus integrity + Saleor version hard gate vs golden corpus |
| `just self-check` | Replay golden corpus against official Saleor |
| `just corpus-diff` | Diff live Saleor vs on-disk reference (L1 + L3) |
| `just patch-corpus` | Incrementally patch L1 probes and/or L3 bundles |
| `just export-reference` | Copy runtime reference volume from container to `./reference/` (git) |
| `just import-reference` | Rebuild harness-backend after pulling corpus changes from git |
| `just record-reference` | Full L1 re-record (+ L3 sync/record unless `--no-client-sync`) |
| `just logs api` | Logs: `api`, `worker`, `backend`, `frontend`, `db`, `saleor-db` |
| `just status` | `docker compose ps` |

Corpus commands use local Saleor defaults (`saleor-api:8000`, admin creds from env). Pass extra flags to the underlying script, e.g. `just patch-corpus --sync-client`.

Version upgrades: `bash scripts/upgrade-reference.sh 3.24.0` (not a just recipe).

## Golden baseline

Before trusting the platform or testing other backends, official Saleor must pass:

```bash
just up
just baseline
```

`just up` auto-runs Saleor DB migrations and ensures the admin user exists. Use `just fresh` only when wiping volumes.

This runs `verify-corpus` (387 L1 + 415 L3 dashboard + 31 L3 storefront certified, schema gate) then `self-check --scope full+scenarios --require-tier2` (full system: **856** scored endpoints, 100% SGRC).

**Pre-flight:** Before starting a run in the UI, the harness calls `POST /api/runs/validate` (API reachability, version gate, fixture entities). Reports show **compatibility %** and **effective score** (excludes deprecated + data-prerequisite failures). See [docs/DYNAMIC-PROBES.md](docs/DYNAMIC-PROBES.md).

## UI certification smoke (manual)

CLI baseline proves the engine; confirm the report UI separately:

1. `just up` and `just register`
2. Open http://localhost:5999 — start a run (always full-system scope)
3. Saleor URL: `http://localhost:8000/graphql/`, admin email/password from `just fresh`
4. Report page: **Certified YES**, compatibility 100%, **effective score** 100%, L3 bundle count shown

Automated certification logic is covered by `backend/tests/test_certification_api.py` (unit-level gate checks) and `just test-e2e` (full API run).

Optional local git hook (mutation-first guard): `cp scripts/pre-commit-mutation-first.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` (requires host `backend/.venv`).

## Harness-only (external API)

```bash
just up-harness-fast   # or just up-harness to rebuild images first
just register
```

Point the UI at your Go/Node/Rust backend URL. Every run uses the full-system scope automatically. Run `just baseline` on official Saleor first — external runs compare against the same golden, not against each other.

**Saleor URL in the UI** (harness backend runs inside Docker):

| Your Saleor runs on | Use in "Saleor Server URL" |
|---------------------|----------------------------|
| Same machine, port 8000 | `http://localhost:8000/graphql/` (rewritten to `host.docker.internal`) |
| Another machine on LAN | Full URL, e.g. `http://192.168.x.x:8000/graphql/` |
| Docker Desktop / explicit host access | `http://host.docker.internal:8000/graphql/` |

## Authentication

Test runs use **Saleor admin email and password** (via `tokenCreate`). Credentials are stored encrypted for **retest** from the report page.

## Compatibility standard

Certification requires **schema gate pass** (L1 + L3) AND **100% SGRC** (Tier 1 + Tier 2 when gate enabled). See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

Official certification scope: **full+scenarios** — L1 (387) + L3 dashboard (415) + L3 storefront (31) + 5 dynamic probes + 15 scenario steps + 3 input variants (**856 scored endpoints**). Deprecated schema-incompatible bundles are excluded from scoring. See [docs/COVERAGE-GAPS.md](docs/COVERAGE-GAPS.md).

## Local verification (no CI)

| Check | Command |
|-------|---------|
| Golden baseline (do this first) | `just baseline` |
| Full local verification | `just verify` |
| Corpus integrity only | `just verify-corpus` |
| Replay only | `just self-check --scope full+scenarios --require-tier2 --min-compat 100` |
| Backend unit tests | `just test` |
| E2E API certification (stack required) | `just test-e2e` |
| Frontend types | `just check` |

## Related

- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — 100% compatibility standard
- [docs/CORPUS-MAINTENANCE.md](docs/CORPUS-MAINTENANCE.md) — incremental corpus workflow (no new just recipes)
- [docs/COVERAGE-GAPS.md](docs/COVERAGE-GAPS.md) — remaining gaps (runtime integrations, richer scenarios)
- [docs/SPEC.md](docs/SPEC.md) — product spec (some sections superseded)
- [docs/saleor-reference-schema.md](docs/saleor-reference-schema.md) — L1 introspection corpus + L3 vendor bundles
- [docs/REFERENCE-SEED.md](docs/REFERENCE-SEED.md) — fixture seeding for L3 certification

`POST /api/reference/capture` records L1 probes from **full Saleor introspection** (all queries and mutations). The legacy `catalog` scope was removed; clients must not send `test_scope`.
