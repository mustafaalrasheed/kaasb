# Kaasb — Navigation Map

## CRITICAL: Token Optimization Rules

Before reading any file, follow these rules:

1. Start every session by reading **only** `CLAUDE.md` and `skills.md` (2 files).
2. Use the **File Index** below to locate what you need — do NOT `find` or `grep` the codebase.
3. For common tasks (new endpoint, new page, translations), use the recipes in `skills.md` without reading example files.
4. Only read a specific file when you are about to **edit** it.
5. When editing, read only the file being changed plus its direct imports (max 3–5 files).
6. Read multiple required files **in parallel** (batch tool calls).
7. After editing, update the Progress Tracker below in one line.

---

## Quick Facts

| Item | Value |
|------|-------|
| Product | Iraqi freelancing marketplace |
| Stack | FastAPI 0.136.0 · Next.js 15.5.15 · PostgreSQL 16 · Redis 7 |
| Python | 3.12 / Uvicorn 0.34.0 / Gunicorn 21.2.0 |
| Frontend | React 19 · TypeScript 5.7.2 · Tailwind 3.4.17 · shadcn/ui |
| Auth | JWT (httpOnly cookies) + Google OAuth + Facebook + Phone OTP |
| Payments | Qi Card ONLY (IQD). Stripe/Wise fully removed. |
| i18n | Cookie-based locale. Arabic primary (RTL). No next-intl. |
| Phase | Production live — beta testing |
| Server | Hetzner CPX22 · 116.203.140.27 · kaasb.com |
| SSH | `ssh -i ~/.ssh/id_ed25519 deploy@116.203.140.27 -p 2222` |
| Owner | Dr. Mustafa Ghassan Abd |

---

## Architecture Summary

**Backend**: Strict Router → Service → DB. Routers in `api/v1/endpoints/` handle HTTP only. Services in `services/` hold all business logic using `AsyncSession`. Models use SQLAlchemy 2.0 `Mapped`/`mapped_column`. Schemas are Pydantic v2. Domain exceptions in `core/exceptions.py` map to HTTP codes in `main.py`.

**Frontend**: Next.js 15 App Router. `src/app/` for pages, `src/components/` for shared UI. SSR for public/SEO pages, CSR for dashboards. All API calls go through `src/lib/api.ts` (axios). Auth state in Zustand (`src/lib/auth-store.ts`). Edge middleware (`src/middleware.ts`) protects `/dashboard` and `/admin`.

**Auth**: JWT access tokens (30 min) + refresh tokens (7 days) in DB. Delivered as httpOnly cookies. Refresh token read from cookie at `/auth/refresh`. Social login via `POST /auth/social`. Phone OTP delivered via email (beta — Twilio in roadmap).

**Payments**: Client pays via Qi Card (redirect flow) → funds land in merchant account → `Escrow` table tracks logically → order completes → admin releases to freelancer (minus 10% fee). No payout API — admin manually pays via Qi Card dashboard and clicks "Mark Paid" in Kaasb.

**i18n**: `useLocale()` hook from `src/providers/locale-provider.tsx` in client components. `cookies()` in server components. All translations are inline ternaries (`ar ? 'Arabic' : 'English'`). RTL via `dir="rtl"` at root.

---

## File Index

### Backend Core

| File | Purpose | Key exports |
|------|---------|-------------|
| `backend/app/main.py` | App factory: CORS, Sentry, Prometheus, middleware, routes | `app` (FastAPI instance) |
| `backend/app/core/config.py` | Settings via pydantic-settings | `settings` singleton |
| `backend/app/core/database.py` | Async engine, session factory | `get_db`, `AsyncSession` |
| `backend/app/core/security.py` | JWT create/verify, password hash/verify | `create_access_token`, `verify_token`, `hash_password`, `verify_password` |
| `backend/app/core/exceptions.py` | Domain exceptions → HTTP codes | `NotFoundError`, `ForbiddenError`, `UnauthorizedError`, `ConflictError`, `BadRequestError`, `RateLimitError`, `ExternalServiceError` |
| `backend/app/api/dependencies.py` | FastAPI DI functions | `get_current_user`, `get_current_admin`, `get_current_freelancer`, `get_current_client`, `get_db` |
| `backend/app/api/v1/router.py` | Aggregates all routers under `/api/v1` | `api_router` |

### Backend Models

| File | Tables | Key columns |
|------|--------|-------------|
| `backend/app/models/base.py` | `BaseModel` | `id` UUID PK, `created_at`, `updated_at` |
| `backend/app/models/user.py` | `users` | `email`, `username`, `hashed_password` (nullable), `primary_role`, `status`, `google_id`, `facebook_id`, `token_version`, `phone`, `skills[]`, `avg_rating`, `last_seen_at` |
| `backend/app/models/refresh_token.py` | `refresh_tokens` | `user_id`, `token_hash`, `expires_at`, `revoked_at` |
| `backend/app/models/phone_otp.py` | `phone_otps` | `phone`, `otp_hash` (SHA-256), `expires_at` (10min), `is_used`, `attempts` (locked at ≥5) |
| `backend/app/models/job.py` | `jobs` | `title`, `category`, `job_type`, `status`, `client_id`, `freelancer_id`, `proposal_count` |
| `backend/app/models/proposal.py` | `proposals` | `job_id`, `freelancer_id`, `bid_amount`, `status`, `cover_letter` |
| `backend/app/models/contract.py` | `contracts`, `milestones` | `client_id`, `freelancer_id`, `status`, `total_amount` |
| `backend/app/models/gig.py` | `gigs`, `gig_packages`, `gig_orders`, `gig_categories`, `gig_subcategories` | `slug`, `status` (pending_review/active/rejected/paused/draft), `freelancer_id`, `category_id`, `rejection_reason`, `reviewed_by_id` (FK→users), `reviewed_at` |
| `backend/app/models/payment.py` | `transactions`, `escrows`, `payment_accounts` | `escrow.status` (pending/funded/released/refunded/disputed), `currency="IQD"` |
| `backend/app/models/message.py` | `conversations`, `messages` | `participant_one_id`, `participant_two_id`, `last_message_at`, `conversation_type` (USER/ORDER/SUPPORT), `order_id`; messages: `sender_role` (CLIENT/FREELANCER/ADMIN/SYSTEM), `is_system`, `attachments` JSONB, `read_at` |
| `backend/app/models/notification.py` | `notifications` | `user_id`, `type` (enum), `is_read`, `link_type`, `link_id`, `actor_id`. Types include: proposal_*, contract_*, milestone_*, payment_*, review_received, new_message, **gig_approved, gig_rejected, gig_submitted**, system_alert |
| `backend/app/models/review.py` | `reviews` | `contract_id`, `reviewer_id`, `reviewee_id`, `rating` (1–5), UNIQUE per contract per party |
| `backend/app/models/report.py` | `reports` | `reporter_id`, `report_type`, `target_id`, `reason`, `status` |

### Backend Services

| File | Purpose | Key methods |
|------|---------|-------------|
| `backend/app/services/auth_service.py` | Register, login, tokens, social, OTP | `register`, `login`, `refresh_token`, `social_login`, `send_phone_otp`, `verify_phone_otp`, `forgot_password`, `reset_password`, `change_password` — password change/reset revokes ALL live refresh tokens + bumps `token_version` |
| `backend/app/services/user_service.py` | Profile CRUD, directory | `get_user`, `update_profile`, `list_freelancers` |
| `backend/app/services/job_service.py` | Job CRUD, search | `create_job`, `update_job`, `search_jobs`, `get_job` |
| `backend/app/services/proposal_service.py` | Proposal lifecycle | `submit_proposal`, `accept_proposal`, `reject_proposal`, `withdraw_proposal` |
| `backend/app/services/contract_service.py` | Contract + milestone lifecycle | `create_contract`, `submit_milestone`, `approve_milestone`, `complete_contract` |
| `backend/app/services/gig_service.py` | Gig CRUD + order lifecycle | `create_gig` (notifies admins), `update_gig`, `search_gigs`, `approve_gig(gig_id, admin)` (validates pending_review, sets audit trail, notifies freelancer), `reject_gig(gig_id, reason, admin)` (same), `place_order`, `deliver_order`, `complete_order` |
| `backend/app/services/payment_service.py` | Escrow, transactions, payouts | `fund_escrow`, `release_escrow`, `get_summary`, `list_transactions`, `list_pending_payouts` |
| `backend/app/services/admin_service.py` | Admin stats, user/job management | `get_stats`, `list_users`, `update_user_status`, `toggle_superuser(user_id, acting_admin)` (promote/demote; resets primary_role to CLIENT on demote; prevents last-admin removal), `list_pending_escrows`, `release_escrow` |
| `backend/app/services/message_service.py` | Conversations, messages | `get_or_create_conversation`, `send_message`, `list_conversations`, `mark_read` |
| `backend/app/services/notification_service.py` | Notification CRUD | `create`, `list_for_user`, `mark_read`, `get_unread_count` |
| `backend/app/services/review_service.py` | Review CRUD | `create_review`, `list_for_user` |
| `backend/app/services/email_service.py` | Transactional email via Resend | `send_verification_email`, `send_password_reset`, `send_notification_email`, `send_phone_otp` |
| `backend/app/services/qi_card_client.py` | Qi Card payment gateway | `create_payment`, `verify_payment`, `refund_payment` (raises — no API), `usd_to_iqd` |
| `backend/app/services/websocket_manager.py` | WS connection registry | `connect`, `disconnect`, `send_to_user`, `broadcast` |
| `backend/app/services/base.py` | Base service class | `BaseService(db: AsyncSession)` |

### Backend Endpoints

| File | Prefix | Notable routes |
|------|--------|----------------|
| `backend/app/api/v1/endpoints/auth.py` | `/auth` | register, login, refresh, social, phone/send-otp, phone/verify-otp, ws-ticket |
| `backend/app/api/v1/endpoints/jobs.py` | `/jobs` | CRUD + search + status transitions |
| `backend/app/api/v1/endpoints/proposals.py` | `/proposals` | submit, accept, reject, shortlist, withdraw |
| `backend/app/api/v1/endpoints/contracts.py` | `/contracts` | create, milestones, complete |
| `backend/app/api/v1/endpoints/gigs.py` | `/gigs` | search, CRUD, orders, admin approve/reject |
| `backend/app/api/v1/endpoints/payments.py` | `/payments` | summary, accounts, transactions, escrow, payout |
| `backend/app/api/v1/endpoints/admin.py` | `/admin` | stats, users, jobs, transactions, escrows/release |
| `backend/app/api/v1/endpoints/messages.py` | `/messages` | conversations, send, mark-read |
| `backend/app/api/v1/endpoints/notifications.py` | `/notifications` | list, unread-count, mark-read |
| `backend/app/api/v1/endpoints/reviews.py` | `/reviews` | create, list |
| `backend/app/api/v1/endpoints/reports.py` | `/reports` | submit, admin list/resolve |
| `backend/app/api/v1/endpoints/users.py` | `/users` | profile, avatar, freelancer directory |
| `backend/app/api/v1/endpoints/gdpr.py` | `/gdpr` | data export, account deletion |
| `backend/app/api/v1/endpoints/health.py` | `/health` | liveness, readiness, detailed |
| `backend/app/api/v1/endpoints/ws.py` | `/ws` | WebSocket connections |

### Backend Schemas

| File | Key schemas |
|------|-------------|
| `backend/app/schemas/user.py` | `UserCreate`, `UserOut`, `UserUpdate`, `FreelancerOut` |
| `backend/app/schemas/job.py` | `JobCreate`, `JobOut`, `JobSearch` |
| `backend/app/schemas/proposal.py` | `ProposalCreate`, `ProposalOut` |
| `backend/app/schemas/contract.py` | `ContractOut`, `MilestoneCreate`, `MilestoneOut` |
| `backend/app/schemas/gig.py` | `GigCreate`, `GigOut`, `GigPackageCreate`, `GigOrderCreate`, `GigOrderOut` |
| `backend/app/schemas/payment.py` | `TransactionOut`, `EscrowOut`, `PaymentSummary`, `PayoutRequest` |
| `backend/app/schemas/message.py` | `MessageCreate`, `MessageOut`, `ConversationOut` |
| `backend/app/schemas/notification.py` | `NotificationOut` |
| `backend/app/schemas/review.py` | `ReviewCreate`, `ReviewOut` |
| `backend/app/schemas/admin.py` | `AdminStats`, `UserStatusUpdate`, `EscrowReleaseResponse` |

### Backend Utils & Middleware

| File | Purpose |
|------|---------|
| `backend/app/utils/circuit_breaker.py` | QiCard resilience (open/half-open/closed states) |
| `backend/app/utils/retry.py` | `async_retry` decorator for flaky external calls |
| `backend/app/utils/files.py` | Upload validation (size, MIME type) |
| `backend/app/utils/sanitize.py` | Input sanitization (HTML strip, SQL-safe) |
| `backend/app/middleware/security.py` | CSRF, rate limiting, security headers |
| `backend/app/middleware/monitoring.py` | Request context logging, correlation IDs |
| `backend/app/tasks/data_retention.py` | Cron: delete stale notifications/tokens, anonymise old accounts |

### Frontend Pages

| Route | File | Rendering |
|-------|------|-----------|
| `/` | `src/app/page.tsx` | SSR |
| `/gigs` | `src/app/gigs/page.tsx` | SSR+ISR |
| `/gigs/[slug]` | `src/app/gigs/[slug]/page.tsx` | SSR+ISR |
| `/jobs` | `src/app/jobs/page.tsx` | SSR |
| `/jobs/[id]` | `src/app/jobs/[id]/page.tsx` + `job-detail-client.tsx` | SSR+CSR |
| `/jobs/new` | `src/app/jobs/new/page.tsx` | CSR |
| `/freelancers` | `src/app/freelancers/page.tsx` + `freelancers-client.tsx` | SSR+CSR |
| `/profile/[username]` | `src/app/profile/[username]/page.tsx` + `profile-client.tsx` | SSR |
| `/auth/login` | `src/app/auth/login/page.tsx` + `login-client.tsx` | CSR |
| `/auth/register` | `src/app/auth/register/page.tsx` + `register-client.tsx` | CSR |
| `/auth/forgot-password` | `src/app/auth/forgot-password/page.tsx` | CSR |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | CSR |
| `/auth/verify-email` | `src/app/auth/verify-email/page.tsx` | CSR |
| `/dashboard` | `src/app/dashboard/page.tsx` | CSR |
| `/dashboard/gigs` | `src/app/dashboard/gigs/page.tsx` | CSR |
| `/dashboard/gigs/new` | `src/app/dashboard/gigs/new/page.tsx` | CSR |
| `/dashboard/gigs/orders` | `src/app/dashboard/gigs/orders/page.tsx` | CSR |
| `/dashboard/my-jobs` | `src/app/dashboard/my-jobs/page.tsx` | CSR |
| `/dashboard/my-proposals` | `src/app/dashboard/my-proposals/page.tsx` | CSR |
| `/dashboard/contracts` | `src/app/dashboard/contracts/page.tsx` | CSR |
| `/dashboard/contracts/[id]` | `src/app/dashboard/contracts/[id]/page.tsx` | CSR |
| `/dashboard/messages` | `src/app/dashboard/messages/page.tsx` | CSR |
| `/dashboard/notifications` | `src/app/dashboard/notifications/page.tsx` | CSR |
| `/dashboard/payments` | `src/app/dashboard/payments/page.tsx` | CSR |
| `/dashboard/reviews` | `src/app/dashboard/reviews/page.tsx` | CSR |
| `/dashboard/settings` | `src/app/dashboard/settings/page.tsx` | CSR |
| `/dashboard/profile/edit` | `src/app/dashboard/profile/edit/page.tsx` | CSR |
| `/dashboard/jobs/[id]/proposals` | `src/app/dashboard/jobs/[id]/proposals/page.tsx` | CSR |
| `/payment/result` | `src/app/payment/result/page.tsx` | CSR |
| `/admin` | `src/app/admin/page.tsx` | CSR |
| `/privacy` | `src/app/privacy/page.tsx` | SSR |
| `/terms` | `src/app/terms/page.tsx` | SSR |

### Frontend Library

| File | Purpose |
|------|---------|
| `src/lib/api.ts` | Axios client + all API functions. All HTTP calls live here. |
| `src/lib/auth-store.ts` | Zustand auth store: `user`, `login`, `logout`, `register`, `socialLogin` |
| `src/lib/constants.ts` | App-wide constants (categories, statuses, limits) |
| `src/lib/seo.ts` | SEO helper functions (metadata, canonical URLs) |
| `src/lib/utils.ts` | General utilities (cn, formatDate, formatCurrency IQD) |
| `src/lib/use-websocket.ts` | WebSocket hook for real-time events |
| `src/middleware.ts` | Edge: JWT exp check, protects `/dashboard` and `/admin` |
| `src/providers/locale-provider.tsx` | `LocaleProvider` + `useLocale()` hook |
| `src/app/actions/locale.ts` | Server action: set locale cookie |

### Frontend Components

| File | Purpose |
|------|---------|
| `src/components/layout/navbar.tsx` | Main navigation with auth state |
| `src/components/auth/social-login-buttons.tsx` | Google + Facebook OAuth buttons |
| `src/components/auth/phone-login-tab.tsx` | Phone OTP login tab |
| `src/components/gigs/gigs-catalog.tsx` | Gig search/filter grid |
| `src/components/ui/notification-bell.tsx` | Header bell with unread count (polls every 30s) |
| `src/components/ui/language-switcher.tsx` | AR/EN toggle |
| `src/components/ui/pagination.tsx` | Generic paginator |
| `src/components/ui/status-badge.tsx` | Colored status pill |
| `src/components/ui/empty-state.tsx` | Empty list placeholder |
| `src/components/ui/cookie-consent.tsx` | GDPR cookie consent banner |
| `src/components/seo/json-ld.tsx` | JSON-LD structured data |
| `src/components/seo/breadcrumbs.tsx` | SEO breadcrumb nav |

### Frontend Types

| File | Types |
|------|-------|
| `src/types/user.ts` | `User`, `FreelancerProfile` |
| `src/types/job.ts` | `Job`, `JobCreate` |
| `src/types/proposal.ts` | `Proposal` |
| `src/types/contract.ts` | `Contract`, `Milestone` |
| `src/types/payment.ts` | `Transaction`, `Escrow`, `PaymentSummary` |
| `src/types/message.ts` | `Conversation`, `Message` |
| `src/types/notification.ts` | `Notification` |
| `src/types/review.ts` | `Review` |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local dev: backend, frontend, postgres, redis, nginx |
| `docker-compose.prod.yml` | Production: adds monitoring stack |
| `docker/backend/Dockerfile` | Backend image (Python 3.12 slim) |
| `docker/frontend/Dockerfile` | Frontend image (Next.js standalone) |
| `docker/nginx/nginx.conf` | SSL termination, reverse proxy, rate limiting. `location ^~ /api/og` routes to Next.js frontend (before the `/api/` → backend catch-all). |
| `docker/prometheus/prometheus.yml` | Metrics scrape config |
| `docker/grafana/` | Dashboard provisioning |
| `.github/workflows/ci.yml` | Lint + test + build on push to main / PRs |
| `.github/workflows/deploy.yml` | SSH deploy to production (after CI on main) |
| `.github/workflows/release.yml` | Versioned Docker images + GitHub Release (v* tags) |
| `deploy.sh` | `./deploy.sh full|--pull|--migrate|--rollback|--backup|--ssl|--status|--logs` |
| `backend/alembic/` | Database migrations (16 migrations, linear chain) |
| `backend/scripts/create_admin.py` | Create/promote admin user |
| `backend/scripts/seed_categories.py` | Seed 8 Iraqi-market gig categories (idempotent) |
| `backend/mypy.ini` | mypy config with per-module error suppressions |
| `backend/pyproject.toml` | ruff + pytest config |

---

## Conventions

### Python
- `snake_case` everywhere. Type hints on all functions.
- Pydantic v2: `model_dump()`, `model_validate()`. Never `.dict()` or `.from_orm()`.
- SQLAlchemy 2.0: `Mapped[T]` + `mapped_column()`. Never `Column()`.
- `lazy="raise"` on relationships — always use `selectinload()` or `joinedload()`.
- Import order: stdlib → third-party → local (ruff-enforced).
- Raise domain exceptions in services; never raise `HTTPException` in services.
- No SQL in routers. Background tasks: `asyncio.create_task()`.

### TypeScript
- `camelCase` vars/functions, `PascalCase` components/types. Strict mode. No `any`.
- All API calls through `src/lib/api.ts`. Zod for validation. React Hook Form for forms.
- No `console.log` in production code.

### Git
Conventional commits: `feat(scope):`, `fix(scope):`, `chore(scope):`, `docs(scope):`, `refactor(scope):`.
Branches: `main` (production), `develop` (staging), `feature/name`, `fix/name`.

---

## Migration Workflow

```bash
cd backend
alembic revision --autogenerate -m "add_column_x_to_table_y"
# Review alembic/versions/<hash>_add_column_x_to_table_y.py
alembic upgrade head
alembic check   # must show "No new upgrade operations detected"
```

**Migration chain** (25 migrations, linear):
`25c8a4c` → `1f80b6c` → `40dda09` → `8708878` → `ae6a5c3` → `b3f9e2a` → `c7d4e8f` → `d1a2b3c` → `e2b3c4d` → `f3a4b5c6d7e8` (legal_compliance) → `a1b2c3d4e5f6` (gig_marketplace) → `b2c3d4e5f6a7` (qi_card_only) → `c3d4e5f6a7b8` (phone_otp) → `d4e5f6a7b8c9` (schema_drift_fix) → `e5f6a7b8c9d0` (social_ids_nullable_password_iqd) → `f1a2b3c4d5e6` (gig_review_audit + notification_types) → `f2a3b4c5d6e7` (gig_needs_revision + revision_note) → `g3b4c5d6e7f8` (gig_order_payment_wiring) → `h4c5d6e7f8g9` (refresh_tokens session_metadata) → `i5d6e7f8g9h0` (chat_system_phase1: conversation_type, order_id, sender_role, is_system, attachments) → `j6e7f8g9h0i1` (chat_system_phase3: messages.read_at, users.last_seen_at) → `k7f8g9h0i1j2` (prev) → `l8g9h0i1j2k3` (escrow_partial_unique_index) → `m9h0i1j2k3l4` (dispute_system) → `n0i1j2k3l4m5` (normalize_enum_cases)

**Enum creation** (idempotent pattern):
```python
op.execute("DO $$ BEGIN CREATE TYPE foo AS ENUM ('a','b'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
op.create_table('t', sa.Column('status', postgresql.ENUM('a','b', name='foo', create_type=False)))
```

---

## Quick Commands

```bash
# Backend dev
cd backend && uvicorn app.main:app --reload --port 8000

# Backend checks
cd backend && ruff check app/ && mypy app/ && pytest

# Frontend dev
cd frontend && npm run dev

# Frontend checks
cd frontend && npm run build && npm run type-check && npm run lint

# Migrations
cd backend && alembic upgrade head && alembic check

# Docker local
docker compose up -d

# Docker production
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Admin user
cd backend && python scripts/create_admin.py
cd backend && python scripts/create_admin.py --reset

# Seed categories
cd backend && python scripts/seed_categories.py

# Deploy
./deploy.sh full        # full redeploy
./deploy.sh --pull      # pull + restart
./deploy.sh --migrate   # run migrations only
./deploy.sh --rollback  # rollback to previous image
./deploy.sh --backup    # manual backup
./deploy.sh --status    # show running containers + health
./deploy.sh --logs      # tail all service logs

# Grafana (SSH tunnel)
ssh -L 3001:localhost:3001 deploy@116.203.140.27 -p 2222 -N
# then open http://localhost:3001
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | Yes | development | development / staging / production |
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | Yes | redis://localhost:6379/0 | Redis connection URL |
| `SECRET_KEY` | Yes (prod) | auto-gen | JWT signing key (32+ bytes hex) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | Refresh token lifetime |
| `DOMAIN` | Yes (prod) | localhost | Production domain |
| `QI_CARD_API_KEY` | Yes (prod) | — | Qi Card merchant API key |
| `QI_CARD_SANDBOX` | No | true | false = live payments |
| `QI_CARD_CURRENCY` | No | IQD | Currency (always IQD) |
| `RESEND_API_KEY` | No | — | Transactional email via Resend |
| `EMAIL_FROM` | No | noreply@kaasb.com | Sender address |
| `FRONTEND_URL` | No | http://localhost:3000 | Used in email links |
| `SENTRY_DSN` | No | — | Error tracking |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth |
| `FACEBOOK_APP_ID` | No | — | Facebook Login |
| `FACEBOOK_APP_SECRET` | No | — | Facebook Login |
| `PLATFORM_FEE_PERCENT` | No | 10.0 | Commission % |
| `MAX_UPLOAD_SIZE_MB` | No | 10 | Upload size limit |
| `HEALTH_BEARER_TOKEN` | No | — | `/health/detailed` auth token |
| `LOG_LEVEL` | No | INFO | DEBUG/INFO/WARNING/ERROR |
| `DB_USER` | Yes (prod) | — | PostgreSQL username |
| `DB_PASSWORD` | Yes (prod) | — | PostgreSQL password |
| `DB_NAME` | Yes (prod) | — | PostgreSQL database name |
| `REDIS_PASSWORD` | Yes (prod) | — | Redis `--requirepass` password |
| `WEB_CONCURRENCY` | No | 5 | Gunicorn workers |
| `GRAFANA_ADMIN_USER` | No | admin | Grafana username |
| `GRAFANA_ADMIN_PASSWORD` | No | — | Grafana password |
| `GITHUB_REPO` | Yes (CI/CD) | — | `owner/repo` for ghcr.io path |
| `NEXT_PUBLIC_API_URL` | No | http://localhost:8000/api/v1 | Frontend API base |
| `NEXT_PUBLIC_BACKEND_URL` | No | http://localhost:8000 | Frontend asset base URL |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | No | — | Google OAuth (frontend) |
| `NEXT_PUBLIC_FACEBOOK_APP_ID` | No | — | Facebook App ID (frontend) |

---

## Known Issues

| # | Issue | Priority | Added |
|---|-------|----------|-------|
| 1 | ~~**WebSocket per-worker**~~ — **RESOLVED** 2026-04-14: Redis pub/sub (psubscribe) bridges all workers. | ~~High~~ Closed | 2026-04-04 |
| 2 | **QiCard refunds** — no refund API in QiCard v0. `refund_payment()` raises `QiCardError` to force manual flow via merchant portal. | Medium | 2026-04-04 |
| 3 | **QiCard payouts** — no payout API. Admin pays via QiCard dashboard then clicks "Mark Paid" in Kaasb admin. | Medium | 2026-04-04 |
| 4 | **Phone OTP (beta)** — OTP delivered via email. To go live: set `TWILIO_*` env vars and switch `email_service.send_phone_otp` → Twilio in `auth_service.send_phone_otp`. | High | 2026-04-04 |
| 5 | **USD_TO_IQD rate** — hardcoded as `1310.0` in `backend/app/services/qi_card_client.py:60`. Needs live rate API or manual update mechanism. | Medium | 2026-04-04 |
| 6 | ~~**Gig orders → QiCard**~~ — **RESOLVED** 2026-04-14: `place_order` creates Escrow + Transaction; `complete_order` releases escrow (migration g3b4c5d6e7f8). | ~~Medium~~ Closed | 2026-04-04 |
| 7 | **i18n translation files unused** — `src/messages/ar.json` and `en.json` exist as reference but not imported at runtime (all translations are inline ternaries). | Low | 2026-04-04 |

---

## Progress Tracker

| Date | Change |
|------|--------|
| 2026-04-20 | SQLAlchemy enum values_callable fix: added `values_callable=lambda x: [e.value for e in x]` to all 14 Enum columns across user/job/proposal/contract/payment/notification models — without it SQLAlchemy sends enum NAMES (uppercase) not VALUES (lowercase), breaking INSERT after n0i1j2k3l4m5 normalized DB labels; fixed jobduration migration targets (1_to_4_weeks/1_to_3_months/3_to_6_months, not one_to_*); CI now fully green; support modal redesigned as mobile bottom sheet (keyboard-safe, backdrop-tap-close, drag handle, X button, autoFocus) |
| 2026-04-19 | Comprehensive enum normalization (`n0i1j2k3l4m5`): idempotent migration renames ALL uppercase enum labels from initial migration to lowercase (userrole, userstatus, jobtype, experiencelevel, jobduration, jobstatus, proposalstatus, contractstatus, milestonestatus, transactiontype, transactionstatus, paymentaccountstatus, paymentprovider, notificationtype — 13 enum types, ~60 values); fixes admin stats, payment summary, pending payouts, contact_support, and every endpoint that filters by enum status; `AdminEscrowInfo` schema — made contract_id/gig_order_id/milestone_id/milestone_title all Optional (fixes 422 on pending payouts for gig-order escrows); chat/disputes RTL+mobile layout fixes (dir=ltr on message containers, AbortController for stale fetch, mobile panel toggle); admin tab refresh fix (URL-derived tab state, no useState); seed_categories.py import fix (GigCategory→Category) |
| 2026-04-19 | Messaging + dispute integration: admin read/write access to ORDER conversations (dispute mediation); `POST /messages/support` — contact support without knowing admin ID; `GET /admin/orders/{id}/conversation` — admin views order chat; system messages in order chat on dispute open/resolve; "Contact Support" modal in dashboard messages page; new admin Disputes tab (list, view order chat, resolve with release/refund modal, links to message client/freelancer); `gigsApi.raiseDispute`, `listDisputedOrders`, `resolveDispute` frontend API calls; conversation type priority fixed (SUPPORT > ORDER when admin is party) |
| 2026-04-19 | Production-readiness audit + security hardening: HMAC-SHA256 signing of Qi Card redirect URLs (prevents payment forgery); OTP switched to `secrets.randbelow` (was `random.randint`); GigOrder PENDING→IN_PROGRESS auto-transition on payment confirmation; `sanitize_text` no longer html.escapes `&`/quotes (was corrupting DB/API); `notify_background()` with dedicated session (fixes use-after-close in bg tasks); Redis jti blacklist for password-reset token single-use; CORS production override (replace not append, blocks localhost leak); atomic SQL UPDATE for user stats (eliminates race condition); escrow partial unique indexes (`l8g9h0i1j2k3`) allow retry after failed payment; WhatsApp OTP priority chain (WhatsApp→SMS→email, Twilio run_in_executor); full dispute lifecycle (raise/freeze escrow/admin resolve release-or-refund, migration `m9h0i1j2k3l4`); unit tests: `tests/unit/test_payment_security.py` (23 tests across HMAC, OTP, sanitize, PaymentService) |
| 2026-04-18 | Gig image upload built end-to-end: `save_gig_image()`+`delete_gig_image()` in files.py (max 5, magic-byte validated); `add_image()`+`remove_image()` on GigService (flag_modified for ARRAY); `POST /gigs/{id}/images` + `DELETE /gigs/{id}/images/{index}` endpoints; `uploadImage()`+`deleteImage()` in frontend gigsApi; image picker UI with local preview in new-gig Step 1; images uploaded sequentially after gig creation before redirect |
| 2026-04-18 | hourly_rate fully removed (model, schema, service, endpoint, 6 frontend files); hero CTA invisible-button bug fixed (dropped blank placeholder, now falls through to correct SSR state during auth loading); Qi Card account setup label clarified (explains phone is a local label, not sent to API); sort-by-rate options removed from freelancer search |
| 2026-04-18 | Security hardening: session rotation on password change/reset (revoke all refresh tokens + bump token_version); CVE dep bumps — starlette 0.49.1, fastapi 0.136, python-jose 3.4.0, pytest 9.0.3, black 26.3.1, pytest-asyncio 1.3.0, Pillow 12.2, axios 1.12.2, Next.js 15.5.15; admin support inbox (admins read/reply to SUPPORT conversations; participant check relaxed for superusers); CI + deploy green on main (d53bbbd) |
| 2026-04-17 | Chat system Phase 3: migration j6e7f8g9h0i1 (messages.read_at, users.last_seen_at); Redis-backed presence service at `app/services/presence.py` with multi-connection counter; `GET /messages/presence` batch endpoint; read receipts wired into `get_messages` (updates read_at, pushes `messages_read` WS event to sender); typing indicators via inbound WS `typing` events with per-conversation membership cache + 1s rate limit |
| 2026-04-17 | Chat system Phase 1+2: migration i5d6e7f8g9h0 (ConversationType enum, SenderRole enum, conversations.order_id, messages.is_system + attachments JSONB); domain event bus at `app/services/events.py` (MessageSentEvent); message_service decoupled from notifications (publishes events instead); message_subscribers.py handles notification + WS push with own DB sessions; support threads and system messages first-class |
| 2026-04-15 | CI history cleaned (134+ failed/skipped runs deleted → 72/72 green); regenerated frontend package-lock.json (21 drifted packages); switched CI to `npm ci --legacy-peer-deps` for deterministic builds; added reusable regenerate-lockfile.yml workflow |
| 2026-04-15 | Active Sessions feature: migration h4c5d6e7f8g9 (ip_address + last_used_at on refresh_tokens); GET/DELETE /auth/sessions endpoints; device/IP metadata captured on login/social/refresh; Active Sessions UI in /dashboard/settings with per-device revoke |
| 2026-04-14 | Known Issue #6 resolved: gig orders wired to Qi Card payment (Escrow + Transaction created on place_order, escrow released on complete_order, migration g3b4c5d6e7f8) |
| 2026-04-14 | Known Issue #1 resolved: WebSocket Redis pub/sub (psubscribe pattern, cross-worker delivery, Redis-backed WS tickets with in-memory fallback) |
| 2026-04-14 | Admin page refactored: extracted 6 tabs into src/app/admin/tabs/ (1039→280 lines in page.tsx) |
| 2026-04-14 | api.ts split: domain APIs moved to src/lib/api/{auth,users,jobs,...}.ts; api.ts now a thin re-export barrel |
| 2026-04-13 | Auth flash fix, pending gigs 500 fix (selectinload), mobile table min-widths, gig approve/reject/revision status rules, social login flush→commit, all CI errors resolved |
| 2026-04-12 | Admin promote/demote: added "Revoke Admin" button (orange) in admin UI; fixed toggle_superuser to reset primary_role→CLIENT on demotion |
| 2026-04-12 | Gig lifecycle hardened: added reviewed_by_id+reviewed_at audit columns, status-transition validation, GIG_APPROVED/GIG_REJECTED/GIG_SUBMITTED notifications; migration a1b2c3d4e5f6 |
| 2026-04-12 | Pre-beta verification: fixed 6 issues (missing OG image, favicon, icon.svg, apple-touch-icon, nginx /api/og routing, manifest.json RTL); report at tests/pre-beta-report.md — GO with conditions |
| 2026-04-12 | CI/CD audit: fixed mypy.ini option typo (disable_error_codes→disable_error_code), added `from __future__ import annotations` + unquoted Mapped types in review.py, bumped Node 20→22, added release concurrency block |
| 2026-04-12 | Cleanup and token optimization complete — new CLAUDE.md navigation map, skills.md patterns, .claudeignore |
| 2026-04-12 | CI/CD fully green — mypy.ini, npm install fix, release Docker fix |
| 2026-04-10 | Post-launch fixes — CVE-2025-66478 (Next.js), auth store double-unwrap, admin UX |
| 2026-04-05 | All 20 build checkpoints complete, production live |
| 2026-03-25 | Security audit (29 issues) + code quality audit (20 issues) resolved |
