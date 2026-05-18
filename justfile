# Saleor Test Platform — all-in-one test harness
#
# Controls TWO separate Docker compose projects:
#   - saleor-platform      (Saleor e-commerce API + workers + supporting services)
#   - saleor-test-platform (FastAPI test backend + SvelteKit frontend + PostgreSQL)
#
# Usage:
#   just up                 — bring up everything
#   just fresh              — fresh Saleor DB (destroys all data), then up
#   just down               — stop all services
#   just status             — show all container status
#   just logs-api           — tail Saleor API logs
#   just logs-worker        — tail Saleor worker logs
#   just logs-backend       — tail test backend logs
#   just logs-frontend      — tail test frontend logs

# ─────────────────────────────────────────────
# Saleor Platform (e-commerce API)
# ─────────────────────────────────────────────
SP_COMPOSE := "docker compose -p saleor-platform -f /home/nobin/saleor-platform/docker-compose.yml"
SP_UP := "docker compose -p saleor-platform -f /home/nobin/saleor-platform/docker-compose.yml up -d"

# ─────────────────────────────────────────────
# Saleor Test Platform (our test harness)
# ─────────────────────────────────────────────
ST_COMPOSE := "docker compose -p saleor-test-platform -f /home/nobin/saleor-test-platform/docker-compose.yml"
ST_UP := "docker compose -p saleor-test-platform -f /home/nobin/saleor-test-platform/docker-compose.yml up -d"

# Bring up everything (Saleor + test platform)
up:
    @echo "=== Starting Saleor Platform ==="
    {{SP_UP}}
    @echo "=== Starting Test Platform ==="
    {{ST_UP}}
    @echo ""
    @echo "=== Waiting for services ==="
    @sleep 6
    @echo ""
    @echo "=== Health checks ==="
    @curl -sf http://localhost:8000/graphql/ -X POST -H "Content-Type: application/json" -d '{"query":"{ __schema { queryType { name } } }"}' > /dev/null && echo "Saleor GraphQL (8000): OK" || echo "Saleor GraphQL (8000): FAILED"
    @curl -sf http://localhost:5998/api/health > /dev/null && echo "Test Backend (5998): OK" || echo "Test Backend (5998): FAILED"
    @docker exec saleor-test-db pg_isready -U testuser -d testdb > /dev/null 2>&1 && echo "Test DB (5997): OK" || echo "Test DB (5997): FAILED"
    @curl -sf http://localhost:5999/dashboard > /dev/null && echo "Test Frontend (5999): OK" || echo "Test Frontend (5999): FAILED"
    @echo ""
    @echo "=== Saleor credentials ==="
    @echo "  Admin: admin@example.com / admin123456"
    @echo "  GraphQL: http://localhost:8000/graphql/"
    @echo "  Dashboard: http://localhost:9000/"

# Bring up Saleor with a FRESH database (destroys all Saleor data)
fresh:
    @echo "=== Tearing down existing Saleor ==="
    {{SP_COMPOSE}} down --volumes 2>&1 || true
    @echo ""
    @echo "=== Starting fresh Saleor containers ==="
    {{SP_UP}}
    @echo ""
    @echo "=== Waiting for DB to be ready ==="
    sleep 6
    @echo "=== Running migrations ==="
    docker exec saleor-platform-api-1 python3 manage.py migrate --noinput
    @echo "=== Creating admin user ==="
    docker cp /tmp/create_admin.py saleor-platform-api-1:/tmp/ 2>/dev/null || true
    docker exec -e PYTHONPATH=/app saleor-platform-api-1 python3 /tmp/create_admin.py
    @echo "=== Verifying Saleor API ==="
    @sleep 3 && curl -sf http://localhost:8000/graphql/ -X POST -H "Content-Type: application/json" -d '{"query":"{ __schema { queryType { name } } }"}' > /dev/null && echo "Saleor GraphQL: OK" || echo "Saleor GraphQL: FAILED"
    @echo ""
    @echo "=== Starting Test Platform ==="
    {{ST_UP}}
    @echo ""
    @echo "=== Health checks ==="
    @sleep 3
    @curl -sf http://localhost:5998/api/health > /dev/null && echo "Test Backend (5998): OK" || echo "Test Backend (5998): FAILED"
    @docker exec saleor-test-db pg_isready -U testuser -d testdb > /dev/null 2>&1 && echo "Test DB (5997): OK" || echo "Test DB (5997): FAILED"
    @curl -sf http://localhost:5999/dashboard > /dev/null && echo "Test Frontend (5999): OK" || echo "Test Frontend (5999): FAILED"
    @echo ""
    @echo "=== Saleor credentials ==="
    @echo "  Admin: admin@example.com / admin123456"

# Stop all services
down:
    @echo "=== Stopping Saleor Platform ==="
    {{SP_COMPOSE}} down 2>&1 || true
    @echo "=== Stopping Test Platform ==="
    {{ST_COMPOSE}} down 2>&1 || true

# Rebuild and bring up test platform
build:
    {{ST_COMPOSE}} down
    {{ST_COMPOSE}} build --no-cache
    {{ST_UP}}
    @echo "=== Waiting for services ==="
    @sleep 8
    @echo "=== Health checks ==="
    @curl -sf http://localhost:5998/api/health > /dev/null && echo "Test Backend (5998): OK" || echo "Backend (5998): FAILED"
    @curl -sf http://localhost:5999/dashboard > /dev/null && echo "Test Frontend (5999): OK" || echo "Frontend (5999): FAILED"

# Rebuild frontend only
rebuild-frontend:
    {{ST_COMPOSE}} build frontend --no-cache
    {{ST_COMPOSE}} up -d frontend

# Register test user
register-test-user:
    curl -s -X POST http://localhost:5998/api/auth/register \
      -H "Content-Type: application/json" \
      -d '{"email":"test@example.com","password":"testpass123","first_name":"Test","last_name":"User"}'

# ─────────────────────────────────────────────
# Log commands
# ─────────────────────────────────────────────
logs-api:
    docker logs -f saleor-platform-api-1

logs-worker:
    docker logs -f saleor-platform-worker-1

logs-backend:
    docker logs -f saleor-test-backend

logs-frontend:
    docker logs -f saleor-test-frontend

# Show status
status:
    @echo "=== Saleor Platform ==="
    @docker ps -a --filter "label=com.docker.compose.project=saleor-platform"
    @echo ""
    @echo "=== Test Platform ==="
    @docker ps -a --filter "label=com.docker.compose.project=saleor-test-platform"