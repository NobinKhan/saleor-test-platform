#!/usr/bin/env bash
set -euo pipefail

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
    sys.exit(0 if (d.get('data') or {}).get('shop') and not d.get('errors') else 1)
except Exception:
    sys.exit(1)
" "${body}" 2>/dev/null
}

wait_for_saleor_graphql() {
  local payload='{"query":"{ shop { version } }"}'
  local max_attempts="${1:-60}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    local response
    response=$(curl -sf http://localhost:8000/graphql/ \
      -X POST \
      -H "Content-Type: application/json" \
      -d "${payload}" 2>/dev/null) || response=""
    if [ -n "${response}" ] && _saleor_graphql_response_ok "${response}"; then
      echo "Saleor GraphQL (8000): OK"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Saleor GraphQL (8000): FAILED (schema not ready or DB unmigrated)"
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
    response=$(curl -sf http://localhost:8000/graphql/ \
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
        echo "Saleor admin auth (8000): OK"
        return 0
      fi
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Saleor admin auth (8000): FAILED (run: just fresh)"
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
  wait_for_url "http://localhost:5998/api/health" "Harness API (5998)" 30 2 || return 1
  wait_for_harness_db 20 || return 1
  wait_for_url "http://localhost:5999/dashboard" "Harness UI (5999)" 20 2 || return 1
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
  wait_for_url "http://localhost:5998/api/health" "Harness API" 20 2 || return 0
  if curl -sf -X POST http://localhost:5998/api/auth/register \
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
  echo "  Harness UI:     http://localhost:5999"
  echo "  Harness API:    http://localhost:5998"
  if [ "${show_saleor}" = "true" ]; then
    echo "  Saleor GraphQL: http://localhost:8000/graphql/"
  fi
  print_credentials "${show_saleor}"
}

print_credentials() {
  local show_saleor="${1:-true}"
  echo ""
  echo "=== Login credentials ==="
  echo ""
  echo "  Test harness UI — http://localhost:5999/login"
  echo "    Email:    ${HARNESS_USER_EMAIL}"
  echo "    Password: ${HARNESS_USER_PASSWORD}"
  if [ "${show_saleor}" = "true" ]; then
    echo ""
    echo "  Saleor API (New Test Run → auth / GraphQL target)"
    echo "    URL:      http://localhost:8000/graphql/"
    echo "    Email:    ${SALEOR_ADMIN_EMAIL}"
    echo "    Password: ${SALEOR_ADMIN_PASSWORD}"
    echo "    (If login fails, run: just fresh)"
  fi
}
