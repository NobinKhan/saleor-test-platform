# Saleor Test Platform — one compose file, minimal commands
#
# Stack:
#   just up | up-harness | up-harness-fast | down | fresh | register | logs | status
#
# Verification (RAM-safe):
#   just test | check | build-harness | verify
#
# Reference corpus (local Saleor defaults; pass script flags via *extra):
#   just corpus-diff | patch-corpus | record-reference | verify-corpus | self-check
#   just export-reference | import-reference  (volume ↔ git)
#   just record-scenarios | record-golden
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

test-e2e:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/resources.sh"
    source "{{ root }}/scripts/lib/health.sh"
    SALEOR_E2E_URL="${SALEOR_E2E_URL:-http://saleor-api:8000/graphql/}"
    echo "=== E2E: fresh Saleor before certification API test ==="
    just fresh
    docker exec -e PYTHONPATH=/app saleor-api python3 -c \
      "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saleor.settings'); import django; django.setup(); from django.core.cache import cache; cache.clear()" \
      2>/dev/null || true
    {{compose}} exec \
      -e SALEOR_E2E=1 \
      -e SALEOR_E2E_URL="${SALEOR_E2E_URL}" \
      harness-backend pytest tests/test_certification_e2e.py -q

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
    # Runtime volume (patch-corpus when REFERENCE_*_ROOT points at /app/reference/)
    if docker exec harness-backend test -f /app/reference/corpora/registry.json 2>/dev/null; then
      docker cp harness-backend:/app/reference/. "{{ root }}/reference/"
      echo "Exported /app/reference/ (runtime volume) → ./reference/"
    fi
    # Baked image paths (default in docker-compose: /app/reference-baked/*)
    for sub in corpora client-bundles scenarios variants dynamic; do
      if docker exec harness-backend test -d "/app/reference-baked/${sub}" 2>/dev/null; then
        mkdir -p "{{ root }}/reference/${sub}"
        docker cp "harness-backend:/app/reference-baked/${sub}/." "{{ root }}/reference/${sub}/"
        echo "Exported /app/reference-baked/${sub}/ → ./reference/${sub}/"
      fi
    done
    echo "Export complete — commit ./reference/ then run: just import-reference"

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

record-golden source:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Recording golden against fresh Saleor (no populatedb) ==="
    if [ "{{ source }}" = "dashboard" ] || [ "{{ source }}" = "all" ]; then
      echo "--- Recording L3 dashboard bundles ---"
      {{compose}} exec harness-backend \
        python -m app.scripts.patch_corpus \
        --url "http://saleor-api:8000/graphql/" \
        --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
        --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" \
        --client-bundles dashboard:all
    fi
    if [ "{{ source }}" = "storefront" ] || [ "{{ source }}" = "all" ]; then
      echo "--- Recording L3 storefront bundles ---"
      {{compose}} exec harness-backend \
        python -m app.scripts.patch_corpus \
        --url "http://saleor-api:8000/graphql/" \
        --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
        --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" \
        --client-bundles storefront:all
    fi
    echo "GOLDEN RECORD COMPLETE"

record-scenarios scenarios="product-lifecycle,checkout-lifecycle,order-lifecycle":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Recording scenario goldens (seed-profile: harness) ==="
    echo "Ensure Saleor is fresh: just fresh"
    {{compose}} exec harness-backend \
      python -m app.scripts.patch_corpus \
      --url "http://saleor-api:8000/graphql/" \
      --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
      --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" \
      --scenarios "{{ scenarios }}" \
      --seed-profile harness
    mkdir -p "{{ root }}/reference/scenarios"
    docker cp harness-backend:/app/reference-baked/scenarios/. "{{ root }}/reference/scenarios/"
    echo ""
    echo "Scenario goldens exported to ./reference/scenarios/"
    echo "Next: just build-harness && docker volume rm saleor-test-platform_harness_reference 2>/dev/null || true"

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
      --min-storefront-bundles 31 \
      --min-storefront-recorded-ratio 1.0 \
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

# Full local verification (serialized — do not run alongside builds or other RAM-heavy tasks).
# Pass --skip-e2e to omit the long certification API test.
verify *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    source "{{ root }}/scripts/lib/resources.sh"
    source "{{ root }}/scripts/lib/health.sh"

    SKIP_E2E=false
    BASELINE_EXTRA=()
    for arg in {{ extra }}; do
      case "${arg}" in
        --skip-e2e) SKIP_E2E=true ;;
        *) BASELINE_EXTRA+=("${arg}") ;;
      esac
    done

    echo "=== verify: prerequisites ==="
    check_verify_prerequisites true

    declare -A RESULTS
    run_step() {
      local name="$1"
      shift
      echo ""
      echo "=== verify: ${name} ==="
      if "$@"; then
        RESULTS["${name}"]="PASS"
      else
        RESULTS["${name}"]="FAIL"
        echo ""
        echo "VERIFY FAILED at step: ${name}"
        for k in unit types baseline e2e; do
          if [ -n "${RESULTS[$k]:-}" ]; then
            echo "  ${k}: ${RESULTS[$k]}"
          fi
        done
        exit 1
      fi
    }

    run_step unit just test
    run_step types just check
    run_step baseline just baseline "${BASELINE_EXTRA[@]}"

    if [ "${SKIP_E2E}" = "true" ]; then
      echo ""
      echo "=== verify: e2e (skipped) ==="
      RESULTS["e2e"]="SKIP"
    else
      echo ""
      echo "=== verify: fresh Saleor before e2e (baseline mutates target) ==="
      just fresh
      run_step e2e just test-e2e
    fi

    echo ""
    echo "=== VERIFY PASS ==="
    echo "  unit:     ${RESULTS[unit]}"
    echo "  types:    ${RESULTS[types]}"
    echo "  baseline: ${RESULTS[baseline]}"
    echo "  e2e:      ${RESULTS[e2e]}"
