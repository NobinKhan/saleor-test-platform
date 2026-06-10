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
