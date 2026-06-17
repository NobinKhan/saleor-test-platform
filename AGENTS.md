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
| Rebuild harness images (serial) | `just build-harness` |
| Start harness without rebuild | `just up-harness-fast` |
| Start harness with rebuild | `just up-harness` |

Run pytest inside the harness container (`just test`), not on the host without a venv.

## Platform rules

Full compatibility, corpus, and SGRC rules live in [`.cursor/rules/`](.cursor/rules/).

## Current state (2026-06-17)

Score: **99.9% (855/856)** against official Saleor 3.23.7. 1 remaining failure.

### Remaining failure

- `checkout-lifecycle/06_checkout_complete` — scenario schema mismatch (1 structural diff)
- Root cause: scenario goldens must be recorded with `--seed-profile harness` to match the self_check profile
- The `patch_corpus --scenarios` now accepts `--seed-profile` flag
- When recording scenario goldens: `python -m app.scripts.patch_corpus --url ... --email ... --password ... --scenarios checkout-lifecycle --seed-profile harness`
- After recording in container, copy goldens to host: `docker cp harness-backend:/app/reference-baked/scenarios/ checkout-lifecycle/steps/ reference/scenarios/checkout-lifecycle/steps/`
- Then rebuild: `just build-harness`

### Key architecture decisions

- `populatedb` removed from `cmd_fresh()` — fresh runs only create data via mutations
- `self_check.py` uses `demo_seed_profile="harness"` to avoid creating `channel-pln`
- `patch_corpus.py` now accepts `--seed-profile` to match recording/replay profiles
- Goldens must be baked into image (COPY in Dockerfile). After `patch_corpus` writes goldens to container, `docker cp` to host then `just build-harness`

### Data independence

All test entities are created via Saleor mutations (not `populatedb`):
- `_ensure_category()`, `_ensure_warehouse()`, `_ensure_reference_product()`, `_ensure_order()` in `reference_seed.py`
- Order creation requires permission group with full access for admin user
- Warehouse channel assignment is immutable after creation in Saleor 3.23.7

## Next steps to reach 100%

1. Re-record all scenario goldens with `--seed-profile harness` (not just checkout-lifecycle)
2. Copy goldens from container → host, rebuild image
3. Run `just baseline` to verify 100%
4. Commit all changes
