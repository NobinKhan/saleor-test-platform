# Saleor Test Platform

GraphQL compatibility test harness for Saleor APIs: run scripted queries and mutations, watch live progress, and export reports.

Everything runs from **one** [`docker-compose.yml`](docker-compose.yml) in this repo — no `saleor-platform` clone.

## Architecture

| Service | Port | Profile |
|---------|------|---------|
| Saleor GraphQL (`saleor-api`) | 8000 | `saleor` |
| Harness UI (`harness-frontend`) | 5999 | `harness` |
| Harness API (`harness-backend`) | 5998 | `harness` |
| Harness DB (`harness-db`) | 5997 | `harness` |

```text
Browser → harness-frontend:5999 → harness-backend:5998 → saleor-api:8000/graphql/
```

## Quick start

```bash
just up
# Open http://localhost:5999/login
#   Harness UI: test@example.com / testpass123
#   Saleor API (test runs): admin@example.com / admin123456
```

After first install or empty Saleor DB:

```bash
just fresh    # wipes volumes, migrates Saleor, creates admin@example.com / admin123456
```

## Commands

| Command | Description |
|---------|-------------|
| `just up` | Saleor + harness (full local stack) |
| `just up-harness` | Harness only — point tests at an external API (e.g. basmalahub) |
| `just down` | Stop all services |
| `just fresh` | Reset DB volumes + Saleor migrate + admin user |
| `just register` | Create harness user `test@example.com` |
| `just logs api` | Logs: `api`, `worker`, `backend`, `frontend`, `db`, `saleor-db` |
| `just status` | `docker compose ps` |

## Harness-only (external API)

```bash
just up-harness
just register
```

**Saleor URL in the UI** (harness backend runs inside Docker):

| Your Saleor runs on | Use in "Saleor Server URL" |
|---------------------|----------------------------|
| Same machine, port 8000 | `http://localhost:8000/graphql/` (rewritten to `host.docker.internal` inside the container) |
| Another machine on LAN | Full URL, e.g. `http://192.168.x.x:8000/graphql/` (used as-is) |
| Docker Desktop / explicit host access | `http://host.docker.internal:8000/graphql/` |

`localhost` in the UI is **not** the harness container itself — it is rewritten using `SALEOR_GRAPHQL_URL` (default `http://host.docker.internal:8000/graphql/` in compose).

## Authentication

Test runs use **Saleor admin email and password** only (via `tokenCreate`). Credentials are stored encrypted on the run for **retest** from the report page.

## Reference baseline

Reports show the compatibility baseline (default **Saleor Dashboard 3.23.6**) and how many catalog queries/mutations were checked. See [docs/saleor-reference-schema.md](docs/saleor-reference-schema.md).

## Pass / fail classification

| Condition | Status |
|-----------|--------|
| Permission / JWT errors | `warn` |
| Schema / undefined field errors | `fail` |
| HTTP non-200 | `fail` |
| Validation errors on mutations | `warn` |
| Resource not found (probe) | `pass` |
| Clean `data` | `pass` |

## Related

- [docs/SPEC.md](docs/SPEC.md) — product spec
- [basmalahub-commerce](../basmalahub-commerce) — Rust integration tests ([runbook](../basmalahub-commerce/docs/graphql-test-runbook.md))
