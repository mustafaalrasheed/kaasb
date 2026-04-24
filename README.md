# كاسب — منصة العمل الحر العراقية
# Kaasb — Iraqi Freelancing Marketplace

> Connecting Iraqi clients and freelancers. Arabic-first, QiCard payments, real-time chat.

**Production:** https://kaasb.com  
**Server:** Hetzner CPX22 · 116.203.140.27  
**Stack:** FastAPI 0.136 · Next.js 15.5 · Python 3.12 · PostgreSQL 16 · Redis 7 · Docker  
**Status:** Live beta — pushing toward public launch (see `docs/launch/`)

---

## Features

| Module | Description |
|--------|-------------|
| **Auth** | JWT + refresh tokens · Google OAuth · Facebook Login · Iraqi phone OTP (WhatsApp → SMS → email fallback) · email verification · password reset · active-session management with "sign out of all other devices" |
| **Job Marketplace** | Client posts a job · freelancers submit proposals · milestone contracts · fixed-price only (IQD) |
| **Service Marketplace** (was "Gigs", renamed 2026-04-21) | Freelancer-published services with 3-tier packages (Basic / Standard / Premium) · admin moderation · structured delivery + revision flow · 3-day auto-complete · seller levels (F2) · ranking (F7) |
| **Buyer Requests** (F1) | Clients post short briefs; freelancers send offers · bridges Jobs + Services |
| **Disputes** (F5) | Open on active orders · admin resolves release-to-freelancer or refund-to-client · system messages in order chat |
| **Payments** | QiCard only (IQD) · escrow holds with optimistic-lock versioning · 10% platform fee · manual payout queue · dual-control approvals above 500k IQD · admin audit log |
| **Chat & moderation** (F6) | WebSocket (Redis pub/sub cross-worker) · typing indicators · read receipts (double-tick) · presence · file attachments · off-platform-contact filter with escalation (warn → block → 24h suspend) |
| **Notifications** | 20+ event types · in-app + email (Resend, CID-embedded logo) · locale-aware templating (bilingual AR/EN) · per-user opt-out · WS push + bell badge |
| **Profiles** | Public freelancer profiles · skills · portfolio · ratings (mirrored onto services) · seller level badges |
| **Admin** | Stats · users · service moderation · transactions · payout queue · disputes tab · audit log · support inbox · support staff role |
| **Security** | CSRF · rate limiting (Redis) · HSTS · CSP · JWT token rotation on password change · bcrypt · input sanitization · Sentry PII scrubbing · HMAC-signed QiCard redirects |
| **SEO** | SSR + ISR public pages · per-page `generateMetadata` · JSON-LD (Organization, Website, Service, FAQPage) · sitemap · OG images · robots.txt |
| **i18n** | Arabic primary (RTL) · English secondary · cookie-based locale (no next-intl) · inline `ar ?` ternaries with server-set `<html dir/lang>` |
| **Observability** | Prometheus (41 alert rules) · Grafana dashboards · Alertmanager → Discord (critical/high) + email (medium/low) · Sentry · structured JSON logs with correlation IDs · `kaasb_last_backup_timestamp_seconds` textfile metric |
| **Ops & DR** | Nightly 3-stage backup (DB + uploads + configs) · SHA-256 checksums · monthly restore verification · S3-compatible off-site + optional GPG · rolling deploy with auto-rollback on backend health-check failure |
| **Testing** | Backend: ruff + mypy + alembic check + 290+ pytest cases (unit + integration hitting real Postgres) · Frontend: ESLint + tsc + Playwright smoke suite (17 tests) against live kaasb.com on every push-to-main |

---

## Architecture

```
kaasb/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── api/v1/          Routers (HTTP only — no SQL)
│   │   ├── services/        Business logic
│   │   ├── models/          SQLAlchemy 2.0 ORM
│   │   ├── schemas/         Pydantic v2 request/response
│   │   └── core/            Config, DB, security, exceptions
│   ├── alembic/             27 migrations (linear chain)
│   └── tests/               unit/ (20 files) + integration/ (6 files, real Postgres)
├── frontend/                Next.js 15 App Router
│   ├── src/app/             Pages (SSR/CSR/ISR)
│   ├── src/components/      Reusable components
│   └── src/lib/             API client, auth store, utils
├── docker/                  Dockerfiles + configs
├── docs/                    Architecture, API, deployment, maintenance
└── .github/workflows/       CI (lint+test+build) + CD (deploy)
```

Pattern: **Router → Service → DB** (strict). No SQL in routers. No business logic in models.

---

## Quick Start (Development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

### 1. Clone & configure

```bash
git clone https://github.com/mustafaalrasheed/kaasb.git
cd kaasb
cp .env.production.example .env.local
# Edit .env.local — at minimum set DATABASE_URL and REDIS_URL
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_categories.py
python scripts/create_admin.py
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Docker (recommended)

```bash
docker compose up -d
# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

---

## Production Deployment

```bash
# Full deploy (build + migrate + restart)
./deploy.sh full

# Options
./deploy.sh --pull          # Pull latest images only
./deploy.sh --migrate       # Run migrations only
./deploy.sh --rollback      # Rollback to previous image
./deploy.sh --backup        # Manual DB backup
./deploy.sh --ssl           # Renew SSL certificates
./deploy.sh --status        # Health check all services
./deploy.sh --logs          # Tail all container logs
./deploy.sh --create-admin  # Create admin user on server
```

See [docs/deployment-guide.md](docs/deployment-guide.md) for full instructions.

---

## Environment Variables

Copy `.env.production.example` and fill in all values. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` |
| `SECRET_KEY` | Yes | 32+ byte JWT signing key |
| `QI_CARD_API_KEY` | Prod | QiCard merchant API key |
| `RESEND_API_KEY` | Prod | Transactional email (resend.com) |
| `GOOGLE_CLIENT_ID` | Prod | Google OAuth 2.0 client ID |
| `FACEBOOK_APP_ID` | Prod | Facebook Login app ID |
| `SENTRY_DSN` | Prod | Error tracking |
| `NEXT_PUBLIC_API_URL` | Yes | Frontend → backend URL |

Full list: [CLAUDE.md — Environment Variables](CLAUDE.md#environment-variables)

---

## Database

**14 migrations** in a linear chain. Always run:

```bash
cd backend
alembic upgrade head   # Apply all pending migrations
alembic check          # Verify schema matches models (should be 0 diffs)
```

**Key tables:** `users` · `jobs` · `proposals` · `contracts` · `milestones` · `gigs` · `gig_packages` · `gig_orders` · `conversations` · `messages` · `notifications` · `transactions` · `escrows` · `reviews` · `reports` · `refresh_tokens` · `phone_otps`

Full schema: [CLAUDE.md — Database Models](CLAUDE.md#database-models-all-tables--key-columns)

---

## Testing

```bash
# Backend
cd backend
pytest                          # All tests
pytest tests/unit/              # Unit tests only (fast, no DB)
pytest tests/integration/       # Requires DB + Redis
ruff check app/                 # Linting
mypy app/                       # Type checking

# Frontend
cd frontend
npm run build                   # Full build (catches type errors)
npm run type-check              # TypeScript only
npm run lint                    # ESLint
```

---

## API Reference

- **Interactive docs:** http://localhost:8000/docs (Swagger UI)
- **Full reference:** [docs/api-reference.md](docs/api-reference.md)
- **Postman collection:** [docs/api/postman_collection.json](docs/api/postman_collection.json)

Base URL: `https://kaasb.com/api/v1`

All endpoints return:
```json
{ "data": ..., "message": "..." }   // success
{ "detail": "error message" }       // error
```

---

## Monitoring

| Service | Access |
|---------|--------|
| Grafana | `ssh -L 3001:localhost:3001 root@116.203.140.27 -N` → http://localhost:3001 |
| Sentry | https://sentry.io (configured via `SENTRY_DSN`) |
| UptimeRobot | Monitors `/health` every 5 min |
| Prometheus | Internal · port 9090 |
| Health check | `curl https://kaasb.com/api/v1/health` |

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Complete project reference — architecture, models, conventions, env vars |
| [docs/architecture.md](docs/architecture.md) | System design, data flow, component interaction |
| [docs/api-reference.md](docs/api-reference.md) | All endpoints with request/response examples |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Step-by-step production deployment |
| [docs/maintenance-guide.md](docs/maintenance-guide.md) | Daily/weekly/monthly operations, emergency procedures |
| [docs/git-workflow.md](docs/git-workflow.md) | Branching strategy, PR process, hotfix flow |
| [docs/disaster-recovery.md](docs/disaster-recovery.md) | DR procedures and runbooks |

---

## Known Limitations (Beta)

- **Phone OTP** delivers via email (no SMS). Production: wire Twilio credentials.
- **QiCard payouts** are manual — admin pays via QiCard dashboard, clicks "Mark Paid".
- **QiCard refunds** require manual processing via QiCard merchant portal.
- **WebSocket** is per-worker — cross-worker push covered by 5s polling. Post-launch: Redis pub/sub.
- **USD_TO_IQD** rate is hardcoded at 1310. Needs live rate feed or manual update.

---

## Payment Flow

```
Client selects package/job
      ↓
QiCard payment page (redirect)
      ↓
Callback → verify signature → create Escrow (status: funded)
      ↓
Freelancer delivers work
      ↓
Client accepts (or auto-accept after 3 days)
      ↓
Admin releases escrow → Escrow (status: released)
      ↓
Admin pays freelancer via QiCard dashboard
      ↓
Admin clicks "Mark Paid" → Transaction recorded
```

Platform fee: **10%** deducted from freelancer payout.

---

## Contributing

1. Branch from `develop`: `git checkout -b feature/my-feature develop`
2. Follow conventions in [CLAUDE.md — Conventions](CLAUDE.md#conventions)
3. Commit: `feat(scope): description` (conventional commits)
4. Open PR against `develop`
5. CI must pass (lint + type-check + build)
6. Merge → auto-deploys to staging

See [docs/git-workflow.md](docs/git-workflow.md) for full workflow.

---

## License

Private. All rights reserved. © 2026 Dr. Mustafa Ghassan Abd.
