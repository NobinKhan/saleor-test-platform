# Saleor Test Platform

GraphQL compatibility test harness for Saleor APIs: replay official Saleor inputs, compare response contracts, and certify **100% compatibility**.

Everything runs from **one** [`docker-compose.yml`](docker-compose.yml) — no `saleor-platform` clone.

**Reference Saleor version:** `3.23.7` (upgrade only when explicitly requested — see [docs/version-upgrade.md](docs/version-upgrade.md)).

## Architecture

| Service | Port | Profile | Image |
|---------|------|---------|-------|
| Saleor GraphQL (`saleor-api`) | 8000 | `saleor` | Official `ghcr.io/saleor/saleor:3.23.7` |
| Harness UI (`harness-frontend`) | 5999 | `harness` | Bun on `node:20-slim` |
| Harness API (`harness-backend`) | 5998 | `harness` | Chainguard Python |
| Harness DB (`harness-db`) | 5997 | `harness` | Chainguard Postgres |

```text
Browser → harness-frontend:5999 → harness-backend:5998 → target Saleor GraphQL
```

## Quick start

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

## Commands

| Command | Description |
|---------|-------------|
| `just up` | Saleor + harness (full local stack) |
| `just up-harness` | Harness only — point tests at an external API |
| `just down` | Stop all services |
| `just fresh` | Reset DB volumes + Saleor migrate + admin user |
| `just register` | Create harness user `test@example.com` |
| `just baseline` | Golden proof: corpus integrity + 100% replay (L1 + L3, Tier 2) |
| `just verify-corpus` | Check reference corpus on disk (L1 + L3) |
| `just self-check` | Replay golden corpus against official Saleor |
| `just corpus-diff` | Diff live Saleor vs on-disk reference (L1 + L3) |
| `just patch-corpus` | Incrementally patch L1 probes and/or L3 bundles |
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

This runs `verify-corpus` (414 L1 probes + 395 L3 bundles, schema gate) then `self-check --scope full+client --require-tier2` (798 endpoints, 100% SGRC).

## UI certification smoke (manual)

CLI baseline proves the engine; confirm the report UI separately:

1. `just up` and `just register`
2. Open http://localhost:5999 — start a run with **compatibility** mode, scope **`full+client`**
3. Saleor URL: `http://localhost:8000/graphql/`, admin email/password from `just fresh`
4. Report page: **Certified YES**, compatibility 100%, L3 bundle count shown

Automated API certification test (POST run → assert report) is a recommended follow-up — not yet in CI.

## Harness-only (external API)

```bash
just up-harness
just register
```

Point the UI at your Go/Node/Rust backend URL. Use scope **`full+client`** for full certification. Run `just baseline` on official Saleor first — external runs compare against the same golden, not against each other.

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

Official certification scope: **798 endpoints** (414 L1 probes + 384 L3 dashboard bundles on schema-compatible Saleor).

## Local verification (no CI)

| Check | Command |
|-------|---------|
| Golden baseline (do this first) | `just baseline` |
| Corpus integrity only | `just verify-corpus` |
| Replay only | `just self-check --scope full+client --require-tier2 --min-compat 100` |
| Backend unit tests | `docker compose exec harness-backend pytest tests/ -q` |
| Frontend types | `cd frontend && bun run check` |

## Related

- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — 100% compatibility standard
- [docs/SPEC.md](docs/SPEC.md) — product spec (some sections superseded)
- [docs/saleor-reference-schema.md](docs/saleor-reference-schema.md) — catalog reference
- [docs/version-upgrade.md](docs/version-upgrade.md) — version upgrade playbook
