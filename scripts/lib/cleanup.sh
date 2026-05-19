#!/usr/bin/env bash
# Remove stale containers before compose up (fixed container_name conflicts).
set -euo pipefail

CONTAINERS=(
  saleor-db
  saleor-cache
  saleor-api
  saleor-worker
  harness-db
  harness-backend
  harness-frontend
  saleor-test-db
  saleor-test-backend
  saleor-test-frontend
)

cleanup_named_containers() {
  local name
  for name in "${CONTAINERS[@]}"; do
    docker rm -f "${name}" 2>/dev/null || true
  done
  # Legacy stacks from old saleor-platform clone workflow
  docker compose -p saleor-platform down --remove-orphans -t 5 2>/dev/null || true
  for name in saleor-platform-api-1 saleor-platform-worker-1 saleor-platform-db-1 saleor-platform-cache-1; do
    docker rm -f "${name}" 2>/dev/null || true
  done
}
