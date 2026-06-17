# Agent workflow

Guidance for all AI coding agents working in this repository.

## Conventional Commits

When creating git commits, use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `perf`, `ci`

**Scopes (examples):** `harness`, `frontend`, `corpus`, `sgrc`, `docker`, `docs`

**Examples:**

```
fix(harness): repair AI report export syntax
feat(frontend): add authenticated export download helpers
chore(docker): serialize harness image builds
```

Use imperative mood, lowercase subject, no trailing period. Do not use prose-style commit subjects.

## Resource-safe commands

Do not run RAM-heavy tasks in parallel. Prefer these `just` recipes:

| Task | Command |
|------|---------|
| Backend unit tests | `just test` |
| Frontend type check | `just check` |
| Full local verification | `just verify` (add `--skip-e2e` to omit API certification) |
| Rebuild harness images (serial) | `just build-harness` |
| Start harness without rebuild | `just up-harness-fast` |
| Start harness with rebuild | `just up-harness` |
| Record scenario goldens | `just record-scenarios` (after `just fresh`) |
| Export corpus to git | `just export-reference` |

Run pytest inside the harness container (`just test`), not on the host without a venv.

## Platform rules

Full compatibility, corpus, and SGRC rules live in [`.cursor/rules/`](.cursor/rules/).

## Current state (2026-06-17)

Score: **100% (856/856)** against official Saleor 3.23.7 on `just baseline` (`full+scenarios`, Tier 2 gate on).

### Key architecture decisions

- `populatedb` removed from `cmd_fresh()` — fresh runs only create data via mutations (`seed_reference`)
- Single **mutation-first harness** topology for all certification (UI, baseline, E2E, recording)
- `ensure_storefront_session()` runs on every certification run
- `just record-scenarios` / `just record-golden` seed harness topology before recording and export from `/app/reference-baked/`
- `just export-reference` copies both runtime volume (`/app/reference/`) and baked paths (`/app/reference-baked/*`)
- Goldens are baked into the image (`COPY reference/` → `/app/reference-baked/`). After recording: `just export-reference`, then `just build-harness`
- `checkout-lifecycle/06_checkout_complete` records pre-payment contract; email preamble + dummy payment plugin seed support optional success golden later

### Data independence

All test entities are created via Saleor mutations (not `populatedb`):

- `_ensure_category()`, `_ensure_warehouse()`, `_ensure_reference_product()`, `_ensure_order()` in `reference_seed.py`
- Order creation requires permission group with full access for admin user
- Warehouse channel assignment is immutable after creation in Saleor 3.23.7

### Re-recording scenario goldens

```bash
just fresh
just record-scenarios
just build-harness
docker volume rm saleor-test-platform_harness_reference 2>/dev/null || true
just fresh
just baseline
```

### Golden literal lint

`just verify-corpus` / `just baseline` run **blocking** demo-literal lint on baked corpus paths when `GOLDEN_LITERAL_LINT_BLOCKING=true` (default in `docker-compose.yml` and `.env.example`).
