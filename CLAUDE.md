# Kaasb Platform — Claude Code Guide

Iraqi freelancing marketplace. FastAPI + Next.js 15 + PostgreSQL 16 + Redis + Docker.

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2 |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| DB | PostgreSQL 16 (asyncpg driver) |
| Cache | Redis 7 |
| Infra | Docker Compose, Nginx, Let's Encrypt |
| CI/CD | GitHub Actions → Hetzner CPX22 |
| Payments | Qi Card (Iraq — sole payment gateway, IQD currency) |
| Monitoring | Prometheus + Grafana + Alertmanager + Sentry |

## Key Directories

```
backend/
  app/
    api/v1/endpoints/   # Route handlers (auth, jobs, proposals, contracts, messages, ws, ...)
    core/               # config.py, database.py, security.py, exceptions.py
    middleware/         # security.py (CSRF, rate limiting, security headers)
    models/             # SQLAlchemy ORM models
    schemas/            # Pydantic request/response schemas
    services/           # Business logic layer (includes websocket_manager.py)
  alembic/versions/     # Database migrations (12 migrations, linear chain)
  tests/
    unit/               # Fast tests, SQLite in-memory
    integration/        # Require real DB + Redis

frontend/
  src/
    app/                # Next.js App Router pages
    components/         # React components
    lib/                # API client (api.ts), utilities
    middleware.ts       # Edge middleware — JWT expiry check, route protection

docker/
  backend/              # Dockerfile, gunicorn.conf.py
  frontend/             # Dockerfile
  nginx/                # nginx.conf (production reverse proxy)
  prometheus/           # prometheus.yml, alert_rules.yml
  grafana/              # Dashboards, provisioning
  alertmanager/         # alertmanager.yml

scripts/
  validate-env.sh       # Validates .env.production before deploy
  server-setup.sh       # Full server provisioning script (Docker, Nginx, certs)
  seed_categories.py    # Seeds Iraqi market gig categories (idempotent)
  create_admin.py       # Creates admin user; respects ADMIN_PASSWORD env var

.github/workflows/
  ci.yml                # Lint + test + build (push to main/develop)
  deploy.yml            # SSH deploy to production (after CI passes on main)
  staging.yml           # SSH deploy to staging (after CI passes on develop)
  release.yml           # Versioned images + GitHub Release (on v*.*.* tag)
```

## Common Commands

### Backend

```bash
cd backend

# Install deps
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest                           # all tests
pytest tests/unit/               # unit only (fast)
pytest -k "test_auth"            # filter by name
pytest --co -q                   # list tests without running

# Lint
ruff check app/
ruff format app/

# Migrations
alembic upgrade head             # apply all migrations
alembic revision --autogenerate -m "description"  # generate new migration
alembic check                    # verify no pending changes
alembic history                  # show migration chain
```

### Frontend

```bash
cd frontend

npm install
npm run dev           # dev server on :3000
npm run build         # production build
npm run lint          # ESLint
```

### Docker (local dev)

```bash
# Start everything (dev)
docker compose up -d

# Start production stack
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Start monitoring stack
docker compose -f docker-compose.monitoring.yml --env-file .env.production up -d
```

### Deployment

```bash
cd /opt/kaasb

./deploy.sh full           # full deploy
./deploy.sh --pull         # pull new images + restart (fast)
./deploy.sh --migrate      # run migrations only
./deploy.sh --rollback     # revert to previous IMAGE_TAG
./deploy.sh --backup       # manual DB backup
./deploy.sh --ssl          # obtain/renew SSL cert
./deploy.sh --status       # container status
./deploy.sh --logs backend # tail service logs
./deploy.sh --restart      # restart all services
./deploy.sh --stop         # stop all services
./deploy.sh --create-admin # create admin user
```

## Architecture Notes

- **API prefix:** `/api/v1/` — all backend routes under this prefix
- **Health endpoints:** `/api/v1/health` (liveness), `/api/v1/health/ready` (readiness)
- **WebSocket:** `/api/v1/ws?token=<jwt>` — in-memory per Gunicorn worker (not Redis pub/sub yet)
- **Auth:** JWT access tokens (30 min) + refresh tokens (7 days) stored in DB, delivered as httpOnly cookies
- **Auth flow:** Middleware decodes JWT `exp` claim with `atob()` (Edge runtime, no external lib). Expired cookies are deleted on redirect to prevent infinite loops. `/auth/refresh` reads the refresh token from the httpOnly cookie. `/auth/clear-session` clears stale cookies server-side on mid-session 401.
- **Payments:** Qi Card is the sole payment gateway (IQD). Stripe and Wise have been fully removed from the codebase and database schema. `QI_CARD_SANDBOX=true` by default — set to `false` and supply `QI_CARD_API_KEY` for live payments.
- **Gig marketplace:** Fiverr-style — freelancers post services (gigs) with up to 3 pricing packages (Basic/Standard/Premium). Clients browse and order directly. 8 Iraqi-market categories seeded automatically on first deploy.
- **Social login:** Google OAuth and Facebook Login supported. Configured via `GOOGLE_CLIENT_ID`, `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` env vars.
- **Rate limiting:** Redis-backed; fallback to in-memory with 10k key cap
- **CORS:** Restricted to `https://{DOMAIN}` and `https://www.{DOMAIN}` in production

## Environment

- `.env.production.example` — template with all required variables
- `scripts/validate-env.sh` — validates env file before deploy
- Never commit `.env.production` — it's in `.gitignore`

## Migration Workflow

Always generate migrations from models, never write them by hand:

```bash
# 1. Edit models in backend/app/models/
# 2. Generate migration
alembic revision --autogenerate -m "add_column_x_to_table_y"
# 3. Review the generated file in alembic/versions/
# 4. Apply locally to test
alembic upgrade head
# 5. Run alembic check (CI also runs this — fails if pending changes)
alembic check
```

### Migration Conventions

- **Enum types:** PostgreSQL has no `CREATE TYPE IF NOT EXISTS`. Use the `DO $$...EXCEPTION WHEN duplicate_object` pattern for idempotent type creation (see `f3a4b5c6d7e8` and `a1b2c3d4e5f6` for examples).
- **Enum columns in `op.create_table`:** Use `postgresql.ENUM(..., create_type=False)` (not `sa.Enum`) when the type is created separately in the same migration. `sa.Enum` ignores `create_type=False`; `postgresql.ENUM` respects it.
- **DB-only objects:** Performance indexes (`c7d4e8f2a901`) and `audit_log` table (`e2b3c4d5e6f7`) exist in the DB but have no SQLAlchemy model. `alembic/env.py` includes an `include_object` filter that skips reflected-only objects to prevent false-positive `alembic check` failures.
- **Casting enums for DML:** When deleting/updating rows by enum value, cast to text first: `WHERE provider::text ILIKE 'stripe'`. Direct string comparison against an enum column fails if the value is not a valid enum member.

## Production Server

- **Host:** Hetzner CPX22 (3 vCPU / 4 GB / Ubuntu 24.04)
- **Domain:** kaasb.com
- **IP:** 116.203.140.27
- **App dir:** `/opt/kaasb`
- **Backups:** `/opt/kaasb/backups/` (daily at 02:00, 7-day retention)
- **Logs:** `./deploy.sh --logs [service]` or `docker logs kaasb_[service]`
- **Grafana:** SSH tunnel → `ssh -L 3001:localhost:3001 root@SERVER_IP -N` → http://localhost:3001
- **Admin user:** `./deploy.sh --create-admin` (supports `ADMIN_PASSWORD` env var override)

## Known Limitations

- WebSocket state is per-Gunicorn worker — messages only reach clients on the same worker.
  Fix: Redis pub/sub. Not yet implemented.
- Qi Card integration uses sandbox mode by default (`QI_CARD_SANDBOX=true`).
  Set `QI_CARD_SANDBOX=false` and provide `QI_CARD_API_KEY` for live payments.

## Migration Chain (12 migrations)

```
25c8a4c398f9  initial
1f80b6c6f2e9  initialclear
40dda097581c  refresh_tokens_and_login_throttling
8708878f9950  add_refresh_tokens_table
ae6a5c343032  qi_card_payment_integration
b3f9e2a1c456  add_token_version_to_users
c7d4e8f2a901  performance_indexes
d1a2b3c4d5e6  fix_monetary_types
e2b3c4d5e6f7  schema_hardening
f3a4b5c6d7e8  legal_compliance
a1b2c3d4e5f6  gig_marketplace          ← adds gigs, packages, orders, categories
b2c3d4e5f6a7  qi_card_only_payments    ← removes Stripe/Wise from DB schema
```
