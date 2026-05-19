#!/usr/bin/env bash
# Unified stack control: single docker-compose.yml, compose profiles.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
COMPOSE_FILE="${ROOT}/docker-compose.yml"
COMPOSE=(docker compose -f "${COMPOSE_FILE}")

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

cmd_up() {
  local profile="${1:-all}"
  # shellcheck disable=SC2206
  local profiles=($(profile_args "${profile}"))

  cleanup_named_containers

  echo "=== Starting stack (profile: ${profile}) ==="
  "${COMPOSE[@]}" "${profiles[@]}" up -d --build --force-recreate --remove-orphans

  echo ""
  echo "=== Waiting for services ==="
  sleep 5

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
  echo "=== Saleor migrations ==="
  sleep 5
  docker exec saleor-api python3 manage.py migrate --noinput
  echo "=== Saleor admin user ==="
  docker cp "${ROOT}/scripts/create_saleor_admin.py" saleor-api:/tmp/create_saleor_admin.py
  docker exec -e PYTHONPATH=/app saleor-api python3 /tmp/create_saleor_admin.py
  echo ""
  check_full_stack_health || true
  register_harness_user
  print_urls true
}

case "${1:-}" in
  up)           cmd_up "${2:-all}" ;;
  up-harness)   cmd_up harness ;;
  down)         cmd_down ;;
  down-volumes) cmd_down --volumes ;;
  fresh)        cmd_fresh ;;
  *)
    echo "Usage: stack.sh {up|up-harness|down|down-volumes|fresh} [all|harness|saleor]" >&2
    exit 1
    ;;
esac
