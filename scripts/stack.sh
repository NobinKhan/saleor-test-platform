#!/usr/bin/env bash
# Unified stack control: single docker-compose.yml, compose profiles.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
COMPOSE_FILE="${ROOT}/docker-compose.yml"
COMPOSE=(docker compose -f "${COMPOSE_FILE}")

source "${ROOT}/scripts/lib/resources.sh"
source "${ROOT}/scripts/lib/cleanup.sh"
source "${ROOT}/scripts/lib/health.sh"

profile_args() {
  case "${1:-all}" in
    harness) echo "--profile" "harness" ;;
    saleor)  echo "--profile" "saleor" ;;
    all)     echo "--profile" "saleor" "--profile" "harness" ;;
    *)       echo "Unknown profile: $1" >&2; exit 1 ;;
  esac
}

wait_for_saleor_container() {
  local max_attempts="${1:-60}"
  local attempt=1
  while [ "${attempt}" -le "${max_attempts}" ]; do
    if docker ps --filter name=saleor-api --filter status=running -q | grep -q .; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "saleor-api container did not start" >&2
  return 1
}

ensure_saleor_migrated() {
  if ! docker ps --filter name=saleor-api --filter status=running -q | grep -q .; then
    return 0
  fi
  echo ""
  echo "=== Saleor database migrations ==="
  docker exec saleor-api python3 manage.py migrate --noinput
  echo "=== Saleor admin user (if missing) ==="
  docker cp "${ROOT}/scripts/create_saleor_admin.py" saleor-api:/tmp/create_saleor_admin.py
  docker exec -e PYTHONPATH=/app saleor-api python3 /tmp/create_saleor_admin.py \
    || echo "Warning: admin seed skipped (may already exist)"
}

build_harness_images() {
  echo "=== Building harness-backend (serial) ==="
  "${COMPOSE[@]}" --profile harness build harness-backend
  echo "=== Building harness-frontend (serial) ==="
  "${COMPOSE[@]}" --profile harness build harness-frontend
}

cmd_up() {
  local profile="${1:-all}"
  local skip_build="${2:-false}"
  # shellcheck disable=SC2206
  local profiles=($(profile_args "${profile}"))

  cleanup_named_containers

  echo "=== Starting stack (profile: ${profile}) ==="
  if [ "${skip_build}" != "true" ]; then
    case "${profile}" in
      harness|all) build_harness_images ;;
    esac
  fi
  "${COMPOSE[@]}" "${profiles[@]}" up -d --no-build --force-recreate --remove-orphans

  echo ""
  echo "=== Waiting for services ==="
  sleep 5

  if [ "${profile}" != "harness" ]; then
    wait_for_saleor_container 60 || true
    ensure_saleor_migrated
  fi

  echo ""
  echo "=== Health checks ==="
  if [ "${profile}" = "harness" ]; then
    check_harness_health || true
    register_harness_user
    print_urls false
  else
    check_full_stack_health || true
    register_harness_user
    print_urls true
  fi
}

cmd_down() {
  local volumes="${1:-}"
  # shellcheck disable=SC2206
  local profiles=($(profile_args all))
  if [ "${volumes}" = "--volumes" ]; then
    "${COMPOSE[@]}" "${profiles[@]}" down --volumes --remove-orphans -t 10
  else
    "${COMPOSE[@]}" "${profiles[@]}" down --remove-orphans -t 10
  fi
  cleanup_named_containers
  echo "Stack stopped."
}

cmd_fresh() {
  cmd_down --volumes
  cmd_up all
  echo ""
  sleep 5
  ensure_saleor_migrated
  echo "=== Reference seed (L3 fixtures — no populatedb) ==="
  docker compose -f "${COMPOSE_FILE}" exec -T harness-backend \
    python -m app.scripts.seed_reference \
    --url "http://saleor-api:8000/graphql/" \
    --email "${SALEOR_ADMIN_EMAIL:-admin@example.com}" \
    --password "${SALEOR_ADMIN_PASSWORD:-admin123456}" \
    || echo "Warning: reference seed failed (Saleor may still be starting)"
  echo ""
  check_full_stack_health || true
  register_harness_user
  print_urls true
}

case "${1:-}" in
  up)                cmd_up "${2:-all}" ;;
  up-harness)        cmd_up harness ;;
  up-harness-fast)   cmd_up harness true ;;
  down)              cmd_down ;;
  down-volumes)      cmd_down --volumes ;;
  fresh)             cmd_fresh ;;
  *)
    echo "Usage: stack.sh {up|up-harness|up-harness-fast|down|down-volumes|fresh} [all|harness|saleor]" >&2
    exit 1
    ;;
esac
