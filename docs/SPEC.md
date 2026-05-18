# Saleor API Testing Platform — SPEC.md

## 1. Concept & Vision

A web-based platform for testing any Saleor-compatible GraphQL API. Feed it a Saleor server URL + auth token, and the platform will exhaustively verify every Query, Mutation, field, and type — then give you a beautiful report with charts, per-endpoint pass/fail details, and downloadable CSV/JSON reports.

**Personality:** Professional, precise, developer-friendly. Like a medical diagnostic tool for GraphQL APIs — clean white/gray background, sharp green/red status indicators, no clutter.

---

## 2. Design Language

**Aesthetic:** Clinical diagnostic dashboard. Clean, high-information-density, no decorative elements.

**Colors:**
- Background: `#0F1117` (dark charcoal)
- Surface: `#1A1D27` (card background)
- Border: `#2D3143` (subtle separation)
- Primary: `#6366F1` (indigo — action buttons)
- Success: `#22C55E` (green — passing tests)
- Error: `#EF4444` (red — failures)
- Warning: `#F59E0B` (amber — skipped/warnings)
- Text primary: `#F9FAFB`
- Text muted: `#9CA3AF`
- Accent: `#818CF8` (light indigo — links)

**Typography:** Inter (Google Fonts) — clean and readable for data.

**Layout:** Three main views:
1. **Dashboard** — test history, start new test button
2. **Test Runner** — live progress, real-time results
3. **Report** — full breakdown with charts and downloadable report

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (SvelteKit/Bun)                 │
│                  http://localhost:5999                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP REST + WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                  Backend (FastAPI/Python)                    │
│                   http://localhost:5998                       │
│                                                             │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ Auth         │  │ Test Runner   │  │ Report Generator│  │
│  │ (JWT)        │  │ (async)       │  │                 │  │
│  └──────────────┘  └───────────────┘  └─────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          PostgreSQL (via Docker)                      │  │
│  │  tables: users, test_runs, test_results, test_items   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         │ GraphQL introspection + queries
         ▼
┌────────────────────────────┐
│  Saleor Server Under Test  │
│  (user-provided URL)       │
└────────────────────────────┘
```

---

## 4. Data Model

### Users
```
id          UUID PK
email       VARCHAR UNIQUE
password    VARCHAR (hashed)
name        VARCHAR
created_at  TIMESTAMP
```

### TestRuns
```
id              UUID PK
user_id         UUID FK -> users.id
saleor_url      VARCHAR
saleor_token    VARCHAR (encrypted)
saleor_version  VARCHAR (detected)
status          ENUM: running|completed|stopped|failed
started_at      TIMESTAMP
completed_at    TIMESTAMP NULL
total_tests     INT
passed          INT
failed          INT
warnings        INT
skipped         INT
```

### TestResults (per endpoint)
```
id              UUID PK
test_run_id     UUID FK -> test_runs.id
category        ENUM: query|mutation|field|type|auth
endpoint_name   VARCHAR   -- e.g. "products", "productCreate"
endpoint_kind   ENUM: QUERY|MUTATION
field_name      VARCHAR NULL  -- for field-level tests
status          ENUM: pass|fail|skip|warn
input_sent      TEXT    -- GraphQL query/variables
expected        TEXT NULL
actual_response TEXT    -- server response
error_message   TEXT NULL
response_time_ms INT
saleor_field_type VARCHAR NULL  -- expected type
actual_field_type VARCHAR NULL  -- detected type
is_public       BOOLEAN  -- public vs staff-only
created_at      TIMESTAMP
```

### TestItems (structured breakdown)
```
id              UUID PK
test_result_id  UUID FK -> test_results.id
item_key        VARCHAR  -- e.g. "name", "slug", "pricing"
item_status      ENUM: pass|fail|missing|type_mismatch
expected_type   VARCHAR NULL
actual_type     VARCHAR NULL
```

---

## 5. Features & User Flow

### 5.1 Authentication
- **Login/Register** page
- JWT access tokens (1h expiry) + refresh tokens (7d)
- Password hashed with bcrypt

### 5.2 Dashboard
- Table of past test runs (with status badge, date, pass rate)
- **"New Test"** button → opens server config modal
- Click past test → view report

### 5.3 New Test Modal
Fields:
- **Saleor Server URL** — e.g. `https://api.saleor.io/graphql`
- **API Token** (optional) — Bearer token or BFF secret
- **Test Scope:**
  - Full (all queries + mutations)
  - Queries only
  - Mutations only
  - Custom (select domains)
- **Public API only** toggle (skip staff-only endpoints)
- **Concurrency** — how many parallel requests (default: 5)
- **Timeout** — per-request timeout in seconds (default: 30s)

### 5.4 Test Runner (Live Progress)
As tests run, page shows:
- Overall progress bar (X/Y endpoints tested)
- Current endpoint being tested (with animated spinner)
- Real-time log stream:
  ```
  [✓] products (query) — 45ms — OK
  [✗] productCreate (mutation) — 203ms — ERROR: field 'metadata' not found
  [~] checkout (query) — SKIP: requires channel
  [✓] orders (query) — 38ms — OK
  ```
- Live stats: Pass / Fail / Warn / Skip counts
- **Stop** button to abort early

### 5.5 Report View
After test completes:

**Summary Cards (top):**
- Total endpoints tested
- Pass rate (%)
- Avg response time
- Saleor version detected

**Charts:**
- Donut chart: Pass / Fail / Warn / Skip
- Bar chart: Per-category results (products, orders, checkout, etc.)
- Bar chart: Response time distribution (0-50ms, 50-100ms, 100-500ms, 500ms+)
- Line chart: Pass rate trend across test runs (if multiple)

**Full Results Table:**
Columns: Status | Endpoint | Kind | Category | Public | Response Time | Actions
Actions: View Details (expands input/expected/actual)

**Filters:**
- Filter by: status (pass/fail/skip), category, kind, public/private
- Search by endpoint name

**Export Buttons:**
- Download JSON (full structured report)
- Download CSV (spreadsheet-friendly)
- Download PDF (summary + key failures)

### 5.6 Endpoint Detail View
When clicking a failing endpoint:
- GraphQL query/mutation sent
- Variables used
- Expected behavior
- Actual response (pretty-printed JSON)
- Diff view for field-level mismatches
- Suggested fix (if known pattern)

---

## 6. Testing Categories

Tests are organized by Saleor GraphQL domain:

| Category | Description |
|----------|-------------|
| `products` | Product, ProductVariant, ProductType queries/mutations |
| `orders` | Order, OrderLine, Fulfillment queries/mutations |
| `checkout` | Checkout, Cart queries/mutations |
| `payments` | Payment, Transaction queries/mutations |
| `shipping` | ShippingZone, ShippingMethod queries/mutations |
| `discounts` | Sale, Voucher, Promotion queries/mutations |
| `channels` | Channel queries/mutations |
| `categories` | Category queries/mutations |
| `collections` | Collection queries/mutations |
| `attributes` | Attribute, AttributeValue queries/mutations |
| `account` | User, Group, Permission queries/mutations |
| `giftcards` | GiftCard queries/mutations |
| `pages` | Page queries/mutations |
| `warehouse` | Warehouse queries/mutations |
| `meta` | Metadata operations |
| `shop` | Shop-level queries |
| `plugins` | Plugin queries/mutations |
| `webhooks` | Webhook subscription queries/mutations |

---

## 7. Test Strategy

### 7.1 Schema Introspection
On test start:
1. Send `__schema` introspection query
2. Parse all types, fields, mutations, queries
3. Store schema snapshot

### 7.2 Public vs Private Detection
- Public queries: `products`, `categories`, `collections`, `shop`, `checkout`, `shippingMethods`
- Staff-only queries: require `Authorization: Bearer <token>` header
- Attempt with and without token to detect

### 7.3 Query Testing
For each query:
1. Send with minimal variables
2. Verify response is valid JSON with expected field structure
3. Check field types match introspection
4. Measure response time
5. Store pass/fail/response

### 7.4 Mutation Testing
For each mutation:
1. Send with test variables (e.g., create with dummy data)
2. Verify mutation succeeds or fails gracefully
3. Don't commit real data — use test-tenant-safe operations
4. If mutation creates data, try to delete after
5. Store pass/fail/response

### 7.5 Field Type Verification
- Compare introspection `type { name, kind }` against expected Saleor types
- Flag any missing fields
- Flag any type mismatches

---

## 8. API Endpoints (FastAPI)

### Auth
```
POST   /api/auth/register        { email, password, name }
POST   /api/auth/login           { email, password } → { access_token, user }
POST   /api/auth/refresh         { refresh_token }
GET    /api/auth/me              → { user }
```

### Test Runs
```
GET    /api/runs                         → list of test runs
POST   /api/runs                         → create and start new test run
GET    /api/runs/{id}                    → get run status
GET    /api/runs/{id}/stream             → SSE stream of live progress
DELETE /api/runs/{id}                    → stop/abort a running test
GET    /api/runs/{id}/results            → all test results for a run
GET    /api/runs/{id}/results/{result_id} → single result with items
GET    /api/runs/{id}/report             → full report data (for charts)
```

### Report Export
```
GET    /api/runs/{id}/export/json        → download full JSON report
GET    /api/runs/{id}/export/csv         → download CSV report
```

---

## 9. Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Backend API | FastAPI (Python) | Fast, async, great GraphQL lib support, auto OpenAPI |
| Frontend | SvelteKit (Bun) | Already in stack, fast HMR, clean reactive UI |
| Database | PostgreSQL (Docker) | Relational data, complex queries, reports |
| ORM | SQLAlchemy 2.x + asyncpg | Async ORM for FastAPI |
| Auth | python-jose (JWT) + passlib (bcrypt) | Standard JWT auth |
| Charts | Chart.js (CDN) | Simple, good-looking, free |
| File export | Jinja2 (PDF) + csv (CSV) | Server-side PDF generation |

---

## 10. Environment Variables

```
DATABASE_URL=postgresql+asyncpg://saleor_test:password@localhost:5997/saleor_test
JWT_SECRET=<generate-random>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_URL=http://localhost:5999
```

---

## 11. Saleor Reference Schema

For comparison, we use Saleor Cloud API as the reference schema.
Known Saleor version: 3.23 (latest stable as of 2026).

Key reference types:
- Query root fields: ~80 query fields
- Mutation root fields: ~120 mutation fields
- Scalar types: ID, String, Int, Float, Boolean, DateTime, Decimal, JSON, UUID, ...
- Object types: Product, ProductVariant, Order, Checkout, Channel, etc.
- Input types: ProductCreateInput, CheckoutCreateInput, etc.

The platform will detect the Saleor version from the `shop { version }` query.

---

## 12. Non-Goals (out of scope for v1)

- Load/performance testing
- WebSocket/subscription testing
- Real checkout/payment flows with actual money
- Multi-tenant isolation testing
- Frontend E2E testing
- Test scheduling / CI integration