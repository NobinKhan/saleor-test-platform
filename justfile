# Saleor Test Platform — one compose file, minimal commands
#
# Stack:
#   just up | up-harness | up-harness-fast | down | fresh | register | logs | status
#
# Verification (RAM-safe):
#   just test | check | build-harness
#
# Reference corpus (local Saleor defaults; pass script flags via *extra):
#   just corpus-diff | patch-corpus | record-reference | verify-corpus | self-check
#   just export-reference | import-reference  (volume ↔ git)
#
# Golden baseline (official Saleor must pass before testing other backends):
#   just baseline

root := justfile_directory()
compose := "docker compose -f " + root + "/docker-compose.yml"

_run cmd *args:
    #!/usr/bin/env bash
    set -euo pipefail
    exec bash "{{ root }}/scripts/stack.sh" {{ cmd }} {{ args }}

up:
    @just _run up all

up-harness:
    @just _run up-harness

up-harness-fast:
    @just _run up-harness-fast

test *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/resources.sh"
    {{compose}} exec harness-backend pytest tests/ -q {{ extra }}

check:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/resources.sh"
    cd "{{ root }}/frontend" && bun run check

build-harness:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/resources.sh"
    {{compose}} --profile harness build harness-backend
    {{compose}} --profile harness build harness-frontend

down:
    @just _run down

fresh:
    @just _run fresh

register:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/health.sh"
    register_harness_user
    print_credentials true

logs service:
    #!/usr/bin/env bash
    case "{{ service }}" in
      api|saleor-api)     docker logs -f saleor-api ;;
      worker|saleor-worker) docker logs -f saleor-worker ;;
      backend|harness)    docker logs -f harness-backend ;;
      frontend|ui)        docker logs -f harness-frontend ;;
      db|harness-db)      docker logs -f harness-db ;;
      saleor-db)          docker logs -f saleor-db ;;
      *) echo "Unknown service: {{ service }}"; echo "Use: api, worker, backend, frontend, db, saleor-db"; exit 1 ;;
    esac

status:
    @docker compose -f "{{ root }}/docker-compose.yml" ps -a

export-reference:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{ root }}/reference"
    docker cp harness-backend:/app/reference/. "{{ root }}/reference/"
    echo "Exported reference corpus from harness_reference volume to ./reference/"

import-reference:
    #!/usr/bin/env bash
    set -euo pipefail
    just build-harness
    echo "Rebuilt harness images with ./reference/ from git (baked at build time)."
    echo "To reset the runtime volume: just down && docker volume rm saleor-test-platform_harness_reference 2>/dev/null || true"

seed-reference *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.seed_reference \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" {{ extra }}

record-reference *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.record_reference \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" \
      --scope full {{ extra }}

corpus-diff *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.corpus_diff \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" {{ extra }}

patch-corpus *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.patch_corpus \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" {{ extra }}

verify-corpus *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.verify_corpus {{ extra }}

self-check *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    {{compose}} exec harness-backend \
      python -m app.scripts.self_check {{ extra }}

check-corpus-version:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Corpus version + integrity check ==="
    {{compose}} exec harness-backend python -m app.scripts.verify_corpus \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}"
    {{compose}} exec harness-backend python -m app.scripts.check_corpus_version \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}"
    echo "CORPUS VERSION OK"

baseline *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Golden baseline: corpus integrity (L1 + L3) ==="
    {{compose}} exec harness-backend \
      python -m app.scripts.verify_corpus \
      --min-probes 380 \
      --min-client-bundles 410 \
      --min-client-recorded-ratio 1.0 \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}"
    echo ""
    echo "=== Golden baseline: replay vs official Saleor ==="
    {{compose}} exec harness-backend \
      python -m app.scripts.self_check \
      --scope full+scenarios --require-tier2 --min-compat 100 {{ extra }}
    echo ""
    echo "BASELINE PASS"
