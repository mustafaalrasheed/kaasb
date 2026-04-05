# كاسب — منصة العمل الحر العراقية
# Kaasb — Iraqi Freelancing Marketplace

> Connecting Iraqi clients and freelancers. Arabic-first, QiCard payments, real-time chat.

**Production:** https://kaasb.com  
**Server:** Hetzner CPX22 · 116.203.140.27  
**Stack:** FastAPI 0.115 · Next.js 15 · PostgreSQL 16 · Redis 7 · Docker

---

## Features

| Module | Description |
|--------|-------------|
| **Auth** | JWT + refresh tokens · Google OAuth · Facebook Login · Iraqi phone OTP (+964) · email verification · password reset |
| **Job Marketplace** | Post jobs · submit proposals · milestone contracts · fixed & hourly pricing |
| **Gig Marketplace** | Fiverr-style gigs · 3-tier packages (basic/standard/premium) · admin moderation · order flow |
| **Payments** | QiCard only (IQD) · escrow holds · 10% platform fee · manual payout queue |
| **Real-time Chat** | WebSocket per conversation · file/image sharing · unread badges · 5s polling fallback |
| **Notifications** | 15 event types · in-app · email (Resend) · bell dropdown · full history page |
| **Profiles** | Public freelancer profiles · skills · portfolio · ratings · hourly rate |
| **Admin Dashboard** | Platform stats · user management · gig moderation · transaction ledger · payout queue |
| **Dashboards** | Freelancer earnings/gigs/orders · Client orders/saved gigs |
| **Security** | CSRF · rate limiting · security headers · input sanitization · bcrypt |
| **SEO** | SSR public pages · JSON-LD · sitemap · Open Graph · hreflang |
| **i18n** | Arabic primary (RTL) · English secondary · next-intl |
| **Monitoring** | Prometheus · Grafana · Alertmanager · Sentry · UptimeRobot |

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
│   ├── alembic/             14 migrations (linear chain)
│   └── tests/               unit/ + integration/
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
