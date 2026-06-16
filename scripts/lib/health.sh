#!/usr/bin/env bash
set -euo pipefail

# Host ports (match docker-compose.yml / .env.example)
SALEOR_HOST_PORT="${SALEOR_HOST_PORT:-8000}"
HARNESS_BACKEND_HOST_PORT="${HARNESS_BACKEND_HOST_PORT:-5998}"
HARNESS_FRONTEND_HOST_PORT="${HARNESS_FRONTEND_HOST_PORT:-5999}"

HARNESS_API_URL="http://localhost:${HARNESS_BACKEND_HOST_PORT}"
HARNESS_UI_URL="http://localhost:${HARNESS_FRONTEND_HOST_PORT}"
SALEOR_GRAPHQL_URL="http://localhost:${SALEOR_HOST_PORT}/graphql/"
wait_for_url() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-30}"
  local sleep_secs="${4:-2}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    if curl -sf "${url}" >/dev/null 2>&1; then
      echo "${label}: OK"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep "${sleep_secs}"
  done
  echo "${label}: FAILED"
  return 1
}

_saleor_graphql_response_ok() {
  local body="$1"
  python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    if d.get('data') is not None and not d.get('errors'):
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
" "${body}" 2>/dev/null
}

wait_for_saleor_graphql() {
  local payload='{"query":"{ shop { name } }"}'
  local max_attempts="${1:-60}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    local response
    response=$(curl -sf "http://localhost:${SALEOR_HOST_PORT}/graphql/" \
      -X POST \
      -H "Content-Type: application/json" \
      -d "${payload}" 2>/dev/null) || response=""
    if [ -n "${response}" ] && _saleor_graphql_response_ok "${response}"; then
      echo "Saleor GraphQL (${SALEOR_HOST_PORT}): OK"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Saleor GraphQL (${SALEOR_HOST_PORT}): FAILED (schema not ready or DB unmigrated)"
  return 1
}

wait_for_saleor_auth() {
  local email="${SALEOR_ADMIN_EMAIL:-admin@example.com}"
  local password="${SALEOR_ADMIN_PASSWORD:-admin123456}"
  local payload
  payload=$(python3 -c "import json; print(json.dumps({'query':'mutation TokenCreate(\$email: String!, \$password: String!) { tokenCreate(email: \$email, password: \$password) { token errors { message } } }','variables':{'email':'${email}','password':'${password}'}}))")
  local max_attempts="${1:-30}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    local response
    response=$(curl -sf "http://localhost:${SALEOR_HOST_PORT}/graphql/" \
      -X POST \
      -H "Content-Type: application/json" \
      -d "${payload}" 2>/dev/null) || response=""
    if [ -n "${response}" ]; then
      if python3 -c "
import json, sys
d = json.loads(sys.argv[1])
tc = (d.get('data') or {}).get('tokenCreate') or {}
sys.exit(0 if tc.get('token') else 1)
" "${response}" 2>/dev/null; then
        echo "Saleor admin auth (${SALEOR_HOST_PORT}): OK"
        return 0
      fi
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Saleor admin auth (${SALEOR_HOST_PORT}): FAILED (run: just fresh)"
  return 1
}

wait_for_harness_db() {
  local max_attempts="${1:-20}"
  local attempt=1
  while [ "${attempt}" -le "${max_attempts}" ]; do
    if docker exec harness-db pg_isready -U saleor_test -d saleor_test >/dev/null 2>&1; then
      echo "Harness DB (5997): OK"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Harness DB (5997): FAILED"
  return 1
}

check_harness_health() {
  wait_for_url "${HARNESS_API_URL}/api/health" "Harness API (${HARNESS_BACKEND_HOST_PORT})" 30 2 || return 1
  wait_for_harness_db 20 || return 1
  wait_for_url "${HARNESS_UI_URL}/dashboard" "Harness UI (${HARNESS_FRONTEND_HOST_PORT})" 20 2 || return 1
  return 0
}

check_full_stack_health() {
  local saleor_ok=0
  local harness_ok=0
  wait_for_saleor_graphql 60 && saleor_ok=1 || true
  if [ "${saleor_ok}" -eq 1 ]; then
    wait_for_saleor_auth 30 || true
  fi
  check_harness_health && harness_ok=1 || true
  if [ "${saleor_ok}" -eq 0 ]; then
    echo ""
    echo "WARNING: Saleor GraphQL is not ready. If this is a fresh DB, run: just fresh"
    return 1
  fi
  return 0
}

HARNESS_USER_EMAIL="${HARNESS_USER_EMAIL:-test@example.com}"
HARNESS_USER_PASSWORD="${HARNESS_USER_PASSWORD:-testpass123}"
HARNESS_USER_NAME="${HARNESS_USER_NAME:-Test User}"
SALEOR_ADMIN_EMAIL="${SALEOR_ADMIN_EMAIL:-admin@example.com}"
SALEOR_ADMIN_PASSWORD="${SALEOR_ADMIN_PASSWORD:-admin123456}"

register_harness_user() {
  wait_for_url "${HARNESS_API_URL}/api/health" "Harness API" 20 2 || return 0
  if curl -sf -X POST "${HARNESS_API_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${HARNESS_USER_EMAIL}\",\"password\":\"${HARNESS_USER_PASSWORD}\",\"name\":\"${HARNESS_USER_NAME}\"}" \
    >/dev/null 2>&1; then
    echo "Harness test user: registered"
  else
    echo "Harness test user: already exists (use credentials below)"
  fi
}

print_urls() {
  local show_saleor="${1:-true}"
  echo ""
  echo "=== URLs ==="
  echo "  Harness UI:     ${HARNESS_UI_URL}"
  echo "  Harness API:    ${HARNESS_API_URL}"
  if [ "${show_saleor}" = "true" ]; then
    echo "  Saleor GraphQL: ${SALEOR_GRAPHQL_URL}"
  fi
  print_credentials "${show_saleor}"
}

print_credentials() {
  local show_saleor="${1:-true}"
  echo ""
  echo "=== Login credentials ==="
  echo ""
  echo "  Test harness UI — ${HARNESS_UI_URL}/login"
  echo "    Email:    ${HARNESS_USER_EMAIL}"
  echo "    Password: ${HARNESS_USER_PASSWORD}"
  if [ "${show_saleor}" = "true" ]; then
    echo ""
    echo "  Saleor API (New Test Run → auth / GraphQL target)"
    echo "    URL:      ${SALEOR_GRAPHQL_URL}"
    echo "    Email:    ${SALEOR_ADMIN_EMAIL}"
    echo "    Password: ${SALEOR_ADMIN_PASSWORD}"
    echo "    (If login fails, run: just fresh)"
  fi
}

check_verify_prerequisites() {
  local saleor_required="${1:-true}"
  local failed=0

  if ! docker ps --filter name=harness-backend --filter status=running -q | grep -q .; then
    echo "ERROR: harness-backend is not running. Run: just up" >&2
    failed=1
  fi

  if [ "${saleor_required}" = "true" ]; then
    if ! docker ps --filter name=saleor-api --filter status=running -q | grep -q .; then
      echo "ERROR: saleor-api is not running. Run: just up" >&2
      failed=1
    fi
  fi

  if [ "${failed}" -ne 0 ]; then
    return 1
  fi

  wait_for_url "${HARNESS_API_URL}/api/health" "Harness API" 10 2 || failed=1
  if [ "${saleor_required}" = "true" ]; then
    wait_for_saleor_graphql 30 || failed=1
  fi

  return "${failed}"
}
