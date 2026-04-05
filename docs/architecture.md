# Kaasb — System Architecture

## Overview

Kaasb is a two-sided freelancing marketplace. Clients post jobs or order gigs. Freelancers bid on jobs or sell gig services. All payments flow through QiCard (Iraqi dinar). The system is deployed as a Docker Compose stack on a single Hetzner CPX22 server.

---

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      kaasb.com                          │
│                       Nginx                             │
│          SSL termination · rate limiting · gzip         │
└─────────────┬──────────────────────┬────────────────────┘
              │                      │
     ┌────────▼───────┐    ┌─────────▼──────┐
     │  Next.js 15    │    │  FastAPI 0.115  │
     │  (standalone)  │    │  (Gunicorn x5)  │
     │  port 3000     │    │  port 8000      │
     └────────────────┘    └────────┬────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
     ┌────────▼───────┐  ┌──────────▼──────┐  ┌──────────▼──────┐
     │ PostgreSQL 16  │  │   Redis 7        │  │   Prometheus    │
     │ port 5432      │  │   port 6379      │  │   + Grafana     │
     │ Primary DB     │  │   Cache+Sessions │  │   port 3001     │
     └────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Backend Architecture

### Pattern: Router → Service → DB (strictly enforced)

```
HTTP Request
    │
    ▼
api/v1/endpoints/*.py      ← Routers: validate input, call service, return response
    │                         NO SQL here. NO business logic here.
    ▼
services/*.py              ← All business logic. Raise domain exceptions.
    │                         Use AsyncSession via dependency injection.
    ▼
models/*.py                ← SQLAlchemy 2.0 ORM (Mapped + mapped_column syntax)
    │
    ▼
PostgreSQL 16 (asyncpg driver)
```

### Key Directories

```
backend/app/
├── api/
│   ├── v1/
│   │   ├── endpoints/     One file per domain (auth, jobs, gigs, payments, …)
│   │   └── router.py      Aggregates all routers under /api/v1
│   └── dependencies.py    get_current_user, get_current_admin, get_db, …
├── core/
│   ├── config.py          All settings via Pydantic BaseSettings + .env
│   ├── database.py        Async engine, session factory, get_db dependency
│   ├── security.py        JWT creation/verification, password hashing
│   └── exceptions.py      Domain exceptions → mapped to HTTP codes in main.py
├── middleware/
│   ├── security.py        CSRF, rate limiting, security headers
│   └── monitoring.py      Request context, logging filter
├── models/                SQLAlchemy ORM models (one per table group)
├── schemas/               Pydantic v2 schemas (separate In/Out per domain)
├── services/              Business logic (one per domain)
└── utils/
    ├── circuit_breaker.py QiCard resilience
    ├── retry.py           async_retry decorator
    ├── files.py           Upload validation (magic bytes, size, whitelist)
    └── sanitize.py        Input sanitization (XSS prevention)
```

### Exception Handling

Domain exceptions are defined in `core/exceptions.py` and mapped to HTTP status codes in `main.py`. Routers never catch exceptions — they bubble up to the global handler.

```python
# services raise:
raise NotFoundError("Job not found")
raise ForbiddenError("Not your job")
raise ValidationError("Budget must be > 0")

# main.py maps to:
NotFoundError     → 404
ForbiddenError    → 403
ValidationError   → 422
ConflictError     → 409
```

### Async Pattern

All database operations are async via `asyncpg`. Background work uses `asyncio.create_task()` (never `BackgroundTasks` for DB work — session lifecycle issues). Services receive `AsyncSession` via FastAPI dependency injection.

```python
async def create_job(session: AsyncSession, client_id: UUID, data: JobCreate) -> Job:
    job = Job(**data.model_dump(), client_id=client_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    # Fire notification without blocking response
    asyncio.create_task(notify_matching_freelancers(job.id))
    return job
```

---

## Frontend Architecture

### Rendering Strategy

| Route pattern | Strategy | Reason |
|--------------|----------|--------|
| `/` homepage | SSR | SEO, dynamic stats |
| `/jobs`, `/gigs` | SSR + ISR (5 min) | SEO + performance |
| `/jobs/[id]`, `/gigs/[slug]` | SSR + ISR (5 min) | SEO + freshness |
| `/profile/[username]` | SSR + ISR (10 min) | SEO public profile |
| `/dashboard/*` | CSR | Auth-gated, real-time data |
| `/admin/*` | CSR | Auth-gated |
| `/auth/*` | CSR | Interactive forms |

### State Management

- **Auth state:** Zustand (`src/lib/auth-store.ts`) — user object, login/logout/register actions
- **Server state:** Direct API calls via axios (`src/lib/api.ts`) — no global cache layer
- **Forms:** React Hook Form + Zod validation
- **Toast:** Sonner

### API Client

All backend calls go through `src/lib/api.ts`. Axios instance with base URL from `NEXT_PUBLIC_API_URL`. Interceptors handle 401 → clear session → redirect to login.

### Auth Flow (Frontend)

```
Page load
  │
  ▼
middleware.ts (Edge)
  Decode JWT exp from cookie (atob, no verification)
  If expired → delete cookies → redirect /auth/login
  If /dashboard/* or /admin/* → require valid token
  │
  ▼
useAuthStore.getUser() — called in layout
  GET /auth/me with cookie
  Populates Zustand store
  │
  ▼
Component renders with user context
```

---

## Authentication System

### Token Storage

- `access_token` (30 min) — httpOnly cookie, path=`/`
- `refresh_token` (7 days) — httpOnly cookie, path=`/api/v1/auth`, stored in DB

### Token Refresh

Browser → any API call → 401 → `POST /auth/refresh` (refresh cookie sent automatically) → new access token cookie set → retry original request.

### Auth Methods

| Method | Flow |
|--------|------|
| Email/password | bcrypt verify → JWT pair issued |
| Google OAuth | Frontend gets access_token → `POST /auth/social {provider: "google", token}` → backend calls Google userinfo → match or create user |
| Facebook | Same pattern as Google |
| Phone OTP | `POST /auth/phone/send-otp {phone}` → OTP emailed (beta) → `POST /auth/phone/verify-otp {phone, otp}` → JWT pair |

### Security Controls

- `token_version` on User — incremented on logout-all, invalidates all existing access tokens
- `failed_login_attempts` + `locked_until` — brute force protection (5 attempts → 15 min lock)
- Refresh tokens stored as SHA-256 hash (not plaintext)

---

## Payment Architecture

### QiCard Flow

```
1. Client initiates payment
   POST /payments/escrow/fund {amount, contract_id/order_id}
   → qi_card_client.create_payment() → returns redirect URL

2. Client redirected to QiCard payment page

3. QiCard posts callback to /payments/qi-card/callback
   → verify HMAC signature
   → find pending escrow record
   → mark escrow status = "funded"
   → notify freelancer

4. Order/contract proceeds

5. On completion:
   Admin → POST /payments/payout {escrow_id}
   → escrow status = "released"
   → transaction recorded (net_amount = amount - 10% fee)
   → admin pays freelancer manually via QiCard merchant dashboard
   → admin clicks "Mark Paid" → payout transaction created
```

### Escrow States

```
pending → funded → released
                 ↘ refunded
                 ↘ disputed
```

### Circuit Breaker (QiCard Resilience)

`utils/circuit_breaker.py` wraps all QiCard API calls. After 5 consecutive failures, the circuit opens for 60 seconds (fast-fail, no waiting). Prometheus tracks circuit state.

---

## Real-Time Architecture

### WebSocket

- Endpoint: `GET /api/v1/ws/{ticket}` — authenticated via one-time ticket
- Ticket issued: `POST /auth/ws-ticket` → 30-second TTL Redis key
- Manager: `services/websocket_manager.py` — per-worker in-memory connection registry
- Events pushed: new message, notification, order status change

### Known Limitation

WebSocket connections are per-Gunicorn worker (5 workers). A message sent on worker 1 only reaches clients connected to worker 1. Cross-worker delivery is covered by **5-second polling fallback** in the frontend. Post-launch fix: Redis pub/sub channel between workers.

### Polling Fallback

```typescript
// frontend/src/app/dashboard/messages/page.tsx
useEffect(() => {
  const interval = setInterval(fetchMessages, 5000);
  return () => clearInterval(interval);
}, [conversationId]);
```

---

## Database Design Principles

### Migrations

14 migrations in a strict linear chain (Alembic). Always run `alembic check` after changes to verify zero drift.

Never use `op.execute("ALTER TYPE ... ADD VALUE")` without a transaction guard — PostgreSQL requires enum additions to run outside transactions. Pattern used:

```python
# Idempotent enum creation
op.execute("""
DO $$
BEGIN
  CREATE TYPE mystatus AS ENUM ('a', 'b');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
""")
```

### Soft Deletes

Users are soft-deleted (`deleted_at` timestamp). Hard delete only via GDPR endpoint after anonymization. All user queries filter `WHERE deleted_at IS NULL`.

### Indexing Strategy

- All FK columns have indexes
- `jobs.status` + `jobs.client_id` composite (dashboard queries)
- `gigs.slug` unique index (public URL lookup)
- `messages.conversation_id + created_at` composite (chat pagination)
- `notifications.user_id + is_read` composite (bell badge count)
- GIN index on `gigs.tags` array (tag search)

---

## Infrastructure

### Docker Services

| Service | Image | Resources | Purpose |
|---------|-------|-----------|---------|
| `backend` | custom (python:3.12-slim) | ~300 MB | FastAPI via Gunicorn+Uvicorn (5 workers) |
| `frontend` | custom (node:20-alpine) | ~150 MB | Next.js standalone build |
| `postgres` | postgres:16-alpine | ~512 MB RAM | Primary database |
| `redis` | redis:7-alpine | ~512 MB RAM | Cache, sessions, rate limiting |
| `nginx` | nginx:alpine | ~50 MB | Reverse proxy, SSL, rate limiting |
| `prometheus` | prom/prometheus | ~200 MB | Metrics collection |
| `grafana` | grafana/grafana | ~300 MB | Metrics dashboard |
| `alertmanager` | prom/alertmanager | ~50 MB | Alert routing |

### Nginx Responsibilities

- SSL termination (Let's Encrypt, auto-renew via certbot)
- HTTP → HTTPS redirect
- www → non-www redirect
- WebSocket proxy (`Upgrade` header handling)
- Rate limiting (login: 5r/m, API: 100r/m, uploads: 10r/m)
- Gzip compression
- Security headers (HSTS, X-Frame-Options, CSP, etc.)
- Static asset caching (Next.js `/_next/static/`)

### Backup Strategy

- `pg_dump` daily at 03:00 UTC → `/opt/kaasb/backups/`
- Retention: 7 daily + 4 weekly
- Restore: `psql kaasb < backup.sql`
- Verify: restore to temp DB weekly, check row counts vs production

---

## Monitoring Stack

| Tool | Purpose | Access |
|------|---------|--------|
| Prometheus | Metrics scraping (FastAPI, Postgres, Redis, Node) | Internal port 9090 |
| Grafana | Dashboards: request rate, latency, error rate, DB connections | SSH tunnel → localhost:3001 |
| Alertmanager | Routes alerts → Telegram/email | Internal |
| Sentry | Exception tracking with stack traces (backend + frontend) | sentry.io |
| UptimeRobot | External `/health` check every 5 min → Telegram alert | uptimerobot.com |

### Key Metrics Tracked

- Request rate and p95 latency per endpoint
- DB connection pool utilization
- Redis memory usage
- Container CPU/memory
- Error rate (4xx/5xx)
- QiCard payment success rate
- Active WebSocket connections

---

## Security Model

| Layer | Control |
|-------|---------|
| Network | UFW: only 22/80/443 open. Fail2ban on SSH. |
| Transport | TLS 1.2+ enforced. HSTS preload. |
| Application | CSRF token (cookie+header double-submit). |
| Auth | JWT with short expiry. Refresh rotation. token_version for revocation. |
| Rate limiting | Per-IP Redis counters. Login 5/min, API 100/min. |
| Input | Pydantic validation + sanitize.py (DOMPurify-equivalent server-side). |
| Files | Magic-byte validation + MIME whitelist + UUID rename + 10 MB limit. |
| SQL | SQLAlchemy parameterized queries. No raw SQL in application code. |
| Secrets | .env files only. Never in code or git history. |
| Dependencies | pip-audit + npm audit in CI. Dependabot PRs weekly. |
