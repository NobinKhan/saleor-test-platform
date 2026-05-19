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
# UI: set Saleor URL to your API, e.g. http://localhost:8000/graphql/
```

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
