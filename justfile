# Saleor Test Platform — one compose file, minimal commands
#
#   just up          — Saleor API + test harness
#   just up-harness  — harness only (external GraphQL target)
#   just down        — stop all services
#   just fresh       — reset volumes, migrate Saleor, create admin
#   just register    — create harness UI user
#   just logs api    — follow container logs

root := justfile_directory()

_run cmd *args:
    #!/usr/bin/env bash
    set -euo pipefail
    exec bash "{{ root }}/scripts/stack.sh" {{ cmd }} {{ args }}

up:
    @just _run up all

up-harness:
    @just _run up-harness

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
