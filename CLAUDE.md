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

## Working Principles

- When assumptions are non-trivial, state them before coding. If multiple reasonable interpretations exist, ask instead of guessing.
- For bugs, write a failing test first when feasible; for features, state success criteria before implementing.

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
| `backend/app/models/user.py` | `users` | `email`, `username`, `hashed_password` (nullable), `primary_role`, `status`, `google_id`, `facebook_id`, `token_version`, `phone`, `skills[]`, `avg_rating`, `last_seen_at`, `seller_level` (new_seller/level_1/level_2/top_rated F2), `total_completed_orders`, `completion_rate`, `response_rate`, `level_updated_at`, `chat_violations`, `chat_suspended_until` (F6) |
| `backend/app/models/refresh_token.py` | `refresh_tokens` | `user_id`, `token_hash`, `expires_at`, `revoked_at` |
| `backend/app/models/phone_otp.py` | `phone_otps` | `phone`, `otp_hash` (SHA-256), `expires_at` (10min), `is_used`, `attempts` (locked at ≥5) |
| `backend/app/models/job.py` | `jobs` | `title`, `category`, `job_type`, `status`, `client_id`, `freelancer_id`, `proposal_count` |
| `backend/app/models/proposal.py` | `proposals` | `job_id`, `freelancer_id`, `bid_amount`, `status`, `cover_letter` |
| `backend/app/models/contract.py` | `contracts`, `milestones` | `client_id`, `freelancer_id`, `status`, `total_amount` |
| `backend/app/models/service.py` | `services`, `service_packages`, `service_orders`, `service_categories`, `service_subcategories`, `service_order_deliveries` | `slug`, `status` (pending_review/active/rejected/paused/draft), `freelancer_id`, `category_id`, `rejection_reason`, `reviewed_by_id`, `requirement_questions` JSONB (F3), `rank_score` (F7); orders: `status` (+pending_requirements F3), `requirement_answers` JSONB, `requirements_submitted_at`; deliveries: `message`, `files[]`, `revision_number` (F4). Renamed from `gig.py` in migration `z2v3w4x5y6z7` (2026-04-21) |
| `backend/app/models/payment.py` | `transactions`, `escrows`, `payment_accounts` | `escrow.status` (pending/funded/released/refunded/disputed), `currency="IQD"`; `payment_accounts.qi_card_phone` + `qi_card_holder_name` (both required before admin can release a payout — manual QiCard app transfer, no API) |
| `backend/app/models/message.py` | `conversations`, `messages` | `participant_one_id`, `participant_two_id`, `last_message_at`, `conversation_type` (USER/ORDER/SUPPORT), `order_id`; messages: `sender_role` (CLIENT/FREELANCER/ADMIN/SYSTEM), `is_system`, `attachments` JSONB, `read_at` |
| `backend/app/models/notification.py` | `notifications` | `user_id`, `type` (enum), `is_read`, `link_type`, `link_id`, `actor_id`. Types include: proposal_*, contract_*, milestone_*, payment_*, review_received, new_message, gig_approved/rejected/submitted, dispute_opened/resolved, **buyer_request_offer_received/accepted/rejected, order_requirements_submitted, order_delivered, order_auto_completed, seller_level_upgraded, chat_violation_warning**, system_alert |
| `backend/app/models/review.py` | `reviews` | `contract_id`, `reviewer_id`, `reviewee_id`, `rating` (1–5), UNIQUE per contract per party |
| `backend/app/models/report.py` | `reports` | `reporter_id`, `report_type`, `target_id`, `reason`, `status` |
| `backend/app/models/buyer_request.py` | `buyer_requests`, `buyer_request_offers` | `client_id`, `status` (open/filled/expired/cancelled), `expires_at`; offers: `freelancer_id`, `gig_id` (nullable), `price`, `status` (pending/accepted/rejected) — F1 |
| `backend/app/models/dispute.py` | `disputes` | `order_id` (UNIQUE), `initiated_by` (client/freelancer), `reason` enum, `description`, `evidence_files[]`, `status` (open/under_review/resolved_refund/resolved_release/cancelled), `admin_id`, `admin_notes`, `resolution`, `resolved_at` — F5 |
| `backend/app/models/violation_log.py` | `violation_logs` | `user_id`, `message_id`, `violation_type` (email/phone/url/external_app), `content_detected`, `action_taken` (warning/blocked/suspended) — F6 |

### Backend Services

| File | Purpose | Key methods |
|------|---------|-------------|
| `backend/app/services/auth_service.py` | Register, login, tokens, social, OTP | `register`, `login`, `refresh_token`, `social_login`, `send_phone_otp`, `verify_phone_otp`, `forgot_password`, `reset_password`, `change_password` — password change/reset revokes ALL live refresh tokens + bumps `token_version` |
| `backend/app/services/user_service.py` | Profile CRUD, directory | `get_user`, `update_profile`, `list_freelancers` |
| `backend/app/services/job_service.py` | Job CRUD, search | `create_job`, `update_job`, `search_jobs`, `get_job` |
| `backend/app/services/proposal_service.py` | Proposal lifecycle | `submit_proposal`, `accept_proposal`, `reject_proposal`, `withdraw_proposal` |
| `backend/app/services/contract_service.py` | Contract + milestone lifecycle | `create_contract`, `submit_milestone`, `approve_milestone`, `complete_contract` |
| `backend/app/services/catalog_service.py` | Service (was "gig") CRUD + order lifecycle | `create_service` (notifies admins), `update_service`, `search_services`, `approve_service(service_id, admin)`, `reject_service(service_id, reason, admin)`, `place_order`, `deliver_order`, `complete_order`. Class renamed to `CatalogService` to avoid `ServiceService` collision with `services/` layer |
| `backend/app/services/payment_service.py` | Escrow, transactions, payouts | `fund_escrow`, `release_escrow`, `get_summary`, `list_transactions`, `list_pending_payouts` |
| `backend/app/services/admin_service.py` | Admin stats, user/job management | `get_stats`, `list_users`, `update_user_status`, `toggle_superuser(user_id, acting_admin)` (promote/demote; resets primary_role to CLIENT on demote; prevents last-admin removal), `list_pending_escrows`, `release_escrow` |
| `backend/app/services/message_service.py` | Conversations, messages | `get_or_create_conversation`, `send_message`, `list_conversations`, `mark_read` |
| `backend/app/services/notification_service.py` | Notification CRUD | `create`, `list_for_user`, `mark_read`, `get_unread_count` |
| `backend/app/services/review_service.py` | Review CRUD | `create_review`, `list_for_user` |
| `backend/app/services/email_service.py` | Transactional email via Resend | `send_verification_email`, `send_password_reset`, `send_notification_email`, `send_phone_otp` |
| `backend/app/services/qi_card_client.py` | Qi Card payment gateway | `create_payment(amount_iqd, ...)`, `verify_payment`, `refund_payment` (raises — no API) |
| `backend/app/services/websocket_manager.py` | WS connection registry | `connect`, `disconnect`, `send_to_user`, `broadcast` |
| `backend/app/services/base.py` | Base service class | `BaseService(db: AsyncSession)` |

### Backend Endpoints

| File | Prefix | Notable routes |
|------|--------|----------------|
| `backend/app/api/v1/endpoints/auth.py` | `/auth` | register, login, refresh, social, phone/send-otp, phone/verify-otp, ws-ticket |
| `backend/app/api/v1/endpoints/jobs.py` | `/jobs` | CRUD + search + status transitions |
| `backend/app/api/v1/endpoints/proposals.py` | `/proposals` | submit, accept, reject, shortlist, withdraw |
| `backend/app/api/v1/endpoints/contracts.py` | `/contracts` | create, milestones, complete |
| `backend/app/api/v1/endpoints/services.py` | `/services` (+ deprecated `/gigs` alias router, drops in Phase 2) | search, CRUD, orders, admin approve/reject |
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
| `backend/app/schemas/service.py` | `ServiceCreate`, `ServiceOut`, `ServicePackageCreate`, `ServiceOrderCreate`, `ServiceOrderOut` |
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
| `/services` | `src/app/services/page.tsx` | SSR+ISR (`/gigs` → 308 redirect via middleware) |
| `/services/[slug]` | `src/app/services/[slug]/page.tsx` | SSR+ISR |
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
| `/dashboard/services` | `src/app/dashboard/services/page.tsx` | CSR (`/dashboard/gigs/*` → 308 redirect) |
| `/dashboard/services/new` | `src/app/dashboard/services/new/page.tsx` | CSR |
| `/dashboard/services/orders` | `src/app/dashboard/services/orders/page.tsx` | CSR |
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
| `src/components/services/services-catalog.tsx` | Service search/filter grid |
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
| `backend/scripts/seed_categories.py` | Seed 8 Iraqi-market service categories (idempotent) |
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

**Migration chain** (27 migrations, linear):
`25c8a4c` → `1f80b6c` → `40dda09` → `8708878` → `ae6a5c3` → `b3f9e2a` → `c7d4e8f` → `d1a2b3c` → `e2b3c4d` → `f3a4b5c6d7e8` (legal_compliance) → `a1b2c3d4e5f6` (gig_marketplace) → `b2c3d4e5f6a7` (qi_card_only) → `c3d4e5f6a7b8` (phone_otp) → `d4e5f6a7b8c9` (schema_drift_fix) → `e5f6a7b8c9d0` (social_ids_nullable_password_iqd) → `f1a2b3c4d5e6` (gig_review_audit + notification_types) → `f2a3b4c5d6e7` (gig_needs_revision + revision_note) → `g3b4c5d6e7f8` (gig_order_payment_wiring) → `h4c5d6e7f8g9` (refresh_tokens session_metadata) → `i5d6e7f8g9h0` (chat_system_phase1: conversation_type, order_id, sender_role, is_system, attachments) → `j6e7f8g9h0i1` (chat_system_phase3: messages.read_at, users.last_seen_at) → `k7f8g9h0i1j2` (prev) → `l8g9h0i1j2k3` (escrow_partial_unique_index) → `m9h0i1j2k3l4` (dispute_system) → `n0i1j2k3l4m5` (normalize_enum_cases) → `o1j2k3l4m5n6` (buyer_requests + new notification types) → `p2k3l4m5n6o1` (seller_levels + F6 user cols) → `q3l4m5n6o1p2` (order_requirements + delivery + ranking) → `r4m5n6o1p2q3` (dispute_model) → `s5n6o1p2q3r4` (violation_logs) → `t6o7p8q9r0s1` (fix missing id indexes) → `u7p8q9r0s1t2` (admin_audit + payout_approvals) → `v8q9r0s1t2u3` (drop_hourly_job_type) → `w9r0s1t2u3v4` (user_is_support_flag) → `x0s1t2u3v4w5` (normalize_phone_format) → `y1u2v3w4x5y6` (add_qi_card_holder_name) → `z2v3w4x5y6z7` (rename_gig_to_service)

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
| `ALERTMANAGER_DISCORD_WEBHOOK_URL` | No | — | Discord webhook for critical/high alerts |
| `ALERTMANAGER_SMTP_FROM` | No | — | Gmail sender address (alert emails) |
| `ALERTMANAGER_SMTP_TO` | No | — | Alert email recipient |
| `ALERTMANAGER_SMTP_AUTH_USERNAME` | No | — | Gmail username |
| `ALERTMANAGER_SMTP_AUTH_PASSWORD` | No | — | Gmail 16-char app password |
| `SKIP_MONITORING` | No | 0 | Set to 1 to skip monitoring stack in deploy.sh |
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
| 2 | **QiCard refunds** — v0 API (current integration) has no refund endpoint. QiCard's **v1 3DS API** (`uat-sandbox-3ds-api.qi.iq`, Basic auth + `X-Terminal-Id`) does expose `POST /api/v1/payment/{paymentId}/refund` (full + partial). Migration requires: confirming merchant provisioning against v1, new env vars (`QI_CARD_V1_HOST`, `QI_CARD_TERMINAL_ID`, Basic-auth creds), persisting the v1 paymentId at create time. Until then `refund_payment()` raises to force manual merchant-portal flow. | Medium | 2026-04-04 (updated 2026-04-20) |
| 3 | **QiCard payouts** — no payout API exists in v0 or v1 3DS (full OpenAPI spec confirms only `POST /payment`, `GET /payment/{id}/status`, `POST /payment/{id}/cancel`, `POST /payment/{id}/refund`). Admin transfers each payout manually via QiCard merchant app to the freelancer's `qi_card_phone` + `qi_card_holder_name` (both now required before the Release button is enabled — migration `y1u2v3w4x5y6`). No automation path. | Medium | 2026-04-04 (updated 2026-04-21) |
| 4 | **Phone OTP (beta)** — OTP delivered via email. To go live: set `TWILIO_*` env vars and switch `email_service.send_phone_otp` → Twilio in `auth_service.send_phone_otp`. | High | 2026-04-04 |
| 5 | ~~**USD_TO_IQD rate**~~ — **RESOLVED** 2026-04-20: Platform is IQD-only. Removed `USD_TO_IQD` constant, `usd_to_iqd()` helper, and all USD conversion paths. `QiCardClient.create_payment` now takes `amount_iqd: int` directly. | ~~Medium~~ Closed | 2026-04-04 |
| 6 | ~~**Gig orders → QiCard**~~ — **RESOLVED** 2026-04-14: `place_order` creates Escrow + Transaction; `complete_order` releases escrow (migration g3b4c5d6e7f8). | ~~Medium~~ Closed | 2026-04-04 |
| 7 | **i18n translation files unused** — `src/messages/ar.json` and `en.json` exist as reference but not imported at runtime (all translations are inline ternaries). | Low | 2026-04-04 |

---

## Progress Tracker

| Date | Change |
|------|--------|
| 2026-04-24 | Post-launch-plan polish + Fiverr-parity #1 + session-reported bug fixes. **Switch-to-selling navbar toggle**: new `useActiveMode` hook (`frontend/src/lib/use-active-mode.ts`) reads/writes `kaasb_active_mode` cookie (365-day Lax); `canToggleMode` gates on authenticated-non-admin; `effectiveMode` drives the existing `showFindWork`/`showPostJob`/etc. flags instead of `primary_role` (75beeb2). **Bug fixes**: language switcher hang — `usersApi.updateLocale` was `await`ed inside `startTransition` despite "fire-and-forget" comment; stale auth → 30s axios timeout → UI frozen (4bed30a). Password reset email replaced 100+ char token URL dump with a single "Click this link" / "اضغط هنا" anchor in both AR + EN templates (6973ea2). Logout 2-click bug — `authApi.logout()` was fire-and-forget so `window.location.href="/"` navigated before server cleared cookies; next page's `initialize()` re-authenticated via still-valid cookies. Now `await authApi.logout()` before navigating (3171a38). **Active sessions bulk action**: new `POST /auth/sessions/revoke-others` keeps current session, revokes all others; `AuthService.revoke_other_sessions(user, keep_token_hash)`; "Sign out of all other devices" button appears when sessions>1 in /dashboard/settings (2174ef4). Conversation type badges reworded "Support"→"Support ticket" / "تذكرة دعم" and "Order"→"Order chat" / "محادثة طلب" so admin-handled threads don't read as role tags (f7c354e). Footer links to /help, /faq, /how-it-works added to layout.tsx; mobile navbar also gets a Help Center link. Playwright smoke suite grew to 17 tests (new `help-pages.smoke.spec.ts`). **Fiverr parity research** (docs/launch/fiverr-parity-notes.md): keep Jobs/Proposals + Services + Buyer Requests; defer AI support widget post-launch; pre-purchase client→freelancer DMs (currently blocked by antispam) to be enhanced with rate limits in Phase 7. **Local dev loop live**: user installed Node.js 24.15.0 + Playwright; `npm run test:smoke` runs the full suite in ~12s against live kaasb.com, 25× faster than CI. Quality-over-speed CI policy set. |
| 2026-04-23 | Professional-launch plan executed through Phase 8 (lean scope). **Phase 1 baseline**: beta-v1 tag, docs/launch/ scaffolding (decision-log + go-no-go-checklist), stale USD→IQD docstring fix. **Phase 2 ops**: wired `kaasb_last_backup_timestamp_seconds` via node_exporter textfile collector so existing `BackupTooOld` alert rule fires (monitoring.yml + backup.sh); fixed 2 latent backup.sh bugs — SIGPIPE under `set -euo pipefail` silently skipped files+configs backups for 16 days (b03ac55), then header-line check `head -1` didn't match pg_dump --format=plain's multi-line header (310d22e); **first full 3-stage backup in prod history ran 2026-04-23**; nginx daily reload cron installed on server so certbot renewals take effect; deploy.yml now includes docker-compose.monitoring.yml + a reconcile step so monitoring changes auto-deploy (09e63f0); Alertmanager smoke-tested end-to-end (critical→Discord <1s, medium→email 5m group_wait, both with auto-resolve notifications). Ops-quickstart doc written. **Phase 3 runbooks**: docs/admin/{dispute,support,payout,refund}-runbook.md — dispute + support complete, payout + refund shipped with `[PENDING QICARD PORTAL WALKTHROUGH]` placeholders (memory file `project_pending_qicard_walkthrough.md` has 19 specific questions for next session). **Phase 5a**: Playwright 1.50.1 installed (`frontend/tests/e2e/*.spec.ts`), CI job `e2e-smoke` runs against live kaasb.com on push-to-main only. **Phase 5b backend integration tests** (`backend/tests/integration/`, 6 files, 18 scenarios): test_service_order_placement, test_escrow_release_on_complete, test_dispute_refund_resolution, test_buyer_request_flow, test_requirements_submission, test_chat_moderation — all hit real Postgres via conftest; pattern `@pytest.mark.asyncio(loop_scope="session")` + patch QiCardClient at import site + `db_session.refresh()` after `synchronize_session=False` UPDATEs documented at `memory/project_backend_integration_test_pattern.md`. **Phase 6 lean**: `docs/launch/error-budgets.md` with 3 weekly budgets (signup→verify ≥95%, escrow-fund ≥99%, dispute-rate ≤2% 30d); full Plausible deferred until WAU>500 (rationale in same doc). **Phase 7 content + SEO**: /services/[slug] split into server page.tsx (generateMetadata + JSON-LD Service schema with price/rating/provider/aggregateRating) + service-detail-client.tsx; new bilingual /help (with SLA commitment published), /faq (20 Q&As, FAQPage JSON-LD for rich results), /how-it-works (client + freelancer 5-step guides); sitemap extended; `serviceDetailMeta()` helper added to seo.ts. **Phase 8**: `docs/admin/support-macros.md` — 8 bilingual canned responses. **Crosscutting quality bars** (decision log): security + SEO + UI/UX + professionalism as continuous bars, not separate phases. `docs/launch/session-summary-2026-04-24.md` is the full handoff. |
| 2026-04-22 | Branch `claude/understand-job-system-v2` (PR #4, draft): continuation of `claude/understand-job-system-NUGQv` after that branch forked from pre-rename main. Cherry-picked 12 PRs onto post-rename main — **payments** PR-P1..P4 (QiCard idempotency+log sanitise+rounding; payout mark-paid flow + min threshold; reconciliation queue + escrow-state metrics; escrow optimistic lock + dispute CHECK + fund atomicity), **notifications** PR-N1..N4 (6 silent state transitions plugged; users.locale + title_ar/en + message_ar/en signature; composite (user_id,is_read) index + WS read event + metrics; archive retention + email delivery + per-user opt-out), **chat** PR-C1..C4 (NFKC+homoglyph+URL-allowlist filter hardening + absolute-URL attachment validators; support-ticket scoping merged into HEAD's support_assignee_id; WS ping + typing TTL + frontend seen-ID dedup + chat attachment upload; per-type masking placeholders + Redis subscriber backoff). Rename reconciliation: dropped PR-C2's redundant migration + `assigned_staff_id` (superseded by main's `support_assignee_id`), replaced its `/claim` method with HEAD's `claim_support_ticket`, kept its `/release` endpoint as `release_support_ticket`. PR-C1's absolute-URL attachment design replaced HEAD's unused `/uploads/`-relative validator. Migration chain: PR-P2's `y1t2u3v4w5x6` rechained behind main's `b4x5y6z7a8b9` (support_ticket_lifecycle). PR-N2's migration `a3v4w5x6y7z8` → PR-N3's `b4w5x6y7z8a9` → PR-N4's `c5x6y7z8a9b0`. PR-P4's `z2u3v4w5x6y7` (escrow version+CHECK). |
| 2026-04-22 | Gig-domain audit + 5 fix PRs. Audit at [docs/audits/gigs-audit.md](docs/audits/gigs-audit.md) — 3 P0, 5 P1 (P1-2 later corrected to "not a bug" — admin unsuspend-chat button already shipped), 4 P2, 4 deferred. **PR-G0** (UI): 3 admin toast strings "Gig"→"Service". **PR-G2** (P0-1+P0-2): both `complete_order` and `auto_complete_delivered_orders` now call `_release_locked_escrow` after `SELECT FOR UPDATE` instead of `release_escrow_by_id` — previous behaviour blocked service-order completion when freelancer's QiCard payout details were incomplete (admin-manual-payout validation was being incorrectly applied to client-driven completion). **PR-G3** (P0-3): new `expire_stale_pending_orders` task in `marketplace_tasks.py` — cancels PENDING service orders >30min old with no FUNDED escrow, atomically decrements `Service.orders_count` so rank_score isn't inflated by abandoned checkouts. **PR-G4** (P1-1): `raise_dispute` now accepts `PENDING_REQUIREMENTS` status (was blocked after F3 landed). **PR-G5** (P1-3): `_update_user_rating` in review_service now mirrors aggregate rating + total_reviews onto every Service the freelancer owns (previously Service.avg_rating was always 0 since reviews are contract-scoped with no service_order path). **PR-G6** (P1-4): `request_revision` now resets due_date to now + min(delivery_days, 3) so revision requests don't instantly flag as OVERDUE against the freelancer's F2 seller-level metric. |
| 2026-04-21 | Phase 1 rename **gig → service / خدمة** (migration `z2v3w4x5y6z7`, atomic PR). Tables: `gigs`→`services`, `gig_packages`→`service_packages`, `gig_orders`→`service_orders`, `gig_categories`→`service_categories`, `gig_subcategories`→`service_subcategories`, `gig_order_deliveries`→`service_order_deliveries`. Enum types renamed: `gigstatus`→`servicestatus`, `gigorderstatus`→`serviceorderstatus`, `gigpackagetier`→`servicepackagetier`. Enum values renamed in `notificationtype` (gig_approved/rejected/submitted/needs_revision → service_*) and `adminauditaction` (gig_approved/rejected → service_*). FK columns renamed (`gig_id`→`service_id` on packages/orders/buyer_request_offers; `gig_order_id`→`service_order_id` on escrows). `notifications.link_type` values updated. Python renames: `Gig→Service` + variants, `GigService→CatalogService` (`backend/app/services/catalog_service.py`) to avoid `ServiceService` collision. Frontend: `/gigs`+`/dashboard/gigs/*` → 308 redirect to `/services`+`/dashboard/services/*` via `middleware.ts`; deprecated `/gigs` alias router on backend kept for one release (removed in Phase 2). Dual-field TS types (`service?: X; gig?: X`) with `(offer.service ?? offer.gig)` coalescing kept during deploy window. Legal pages + i18n reference files swept. EN now reads "Service"; AR was already "خدمة" so no UI-facing AR change. |
| 2026-04-21 | Payout account field (migration `y1u2v3w4x5y6`): added `qi_card_holder_name VARCHAR(128) NULL` on `payment_accounts`. `setup_payment_account` is now an upsert (creates if missing; updates only `qi_card_holder_name` on existing — phone stays immutable post-creation). `release_escrow_by_id` raises `BadRequestError` when freelancer lacks both `qi_card_phone` + `qi_card_holder_name` (gig-order auto-complete bypasses by calling `_release_locked_escrow` directly). Frontend `/dashboard/payments` setup form adds cardholder name input + warns on incomplete accounts; admin payouts tab shows holder name column and disables Release button when fields are missing. Confirmed QiCard v1 3DS OpenAPI surface is 4 endpoints only (payment/status/cancel/refund) — no payout API in v0 or v1. |
| 2026-04-20 | Known Issue #5 resolved: USD→IQD conversion removed. Platform is IQD-only. `USD_TO_IQD` constant + `usd_to_iqd()` helper deleted from `qi_card_client.py`; `QiCardClient.create_payment` signature is now `amount_iqd: int` (was `amount_usd: float`). Updated callers: `gig_service.place_order` (passes `int(price_d)`), `payment_service.fund_escrow` (passes `int(fees["amount"])`), `payment_service.refund_escrow` + `request_payout` (use `int(amount)` directly). Error message for insufficient balance now reads "{N:,.0f} IQD" instead of "${N:.2f}". |
| 2026-04-20 | Ops runbook — monitoring + alerts: Alertmanager swapped from Telegram to Discord (`discord_configs` — Telegram blocked in Iraq); `deploy.sh:57` now includes `docker-compose.monitoring.yml` by default (opt-out via `SKIP_MONITORING=1`); env vars added: `ALERTMANAGER_DISCORD_WEBHOOK_URL`, `ALERTMANAGER_SMTP_{FROM,TO,AUTH_USERNAME,AUTH_PASSWORD}`; user provides nightly backup cron install + env-var population steps manually on server |
| 2026-04-20 | F3 order-requirements UI + F4 delivery UI: `/dashboard/gigs/orders` now shows `pending_requirements` status (amber badge), opens RequirementsModal that reads `order.gig.requirement_questions` and posts `{ answers: [{question, answer}] }` via `gigsApi.submitRequirements`; replaced `window.prompt` delivery flow with structured DeliverModal (message textarea + list of file URLs with URL validation); added `GET /gigs/orders/{id}/deliveries` endpoint + `GigService.list_deliveries` + `gigsApi.listDeliveries` for client-side DeliveryView (paginated-style list of prior deliveries with revision numbers, messages, and external file links) |
| 2026-04-20 | Hourly rate removed from jobs (Kaasb is fixed-price only): `JobType` enum collapsed to single `FIXED` value, migration `v8q9r0s1t2u3` converts stragglers then swaps enum; `JobUpdate` schema pattern `^fixed$`; frontend removes hourly toggle on `/jobs/new`, pricing-type dropdown on `/jobs`, hourly label on `/jobs/[id]`, hourly branch in JSON-LD, `hourly rate` copy in dashboard placeholder + privacy page. SUPPORT role added: `users.is_support` boolean (migration `w9r0s1t2u3v4`), `get_current_staff` dependency (admin OR support), read-only/support-safe admin endpoints widened (stats, users list, jobs list, escrows list, payout-approvals pending, audit logs, transactions, support inbox, order conversations), `POST /admin/users/{id}/toggle-support`, dispute list + assign widened to staff; resolve/release/user-status/admin-toggle/gig-moderation stay admin-only; admin UI hides `gigs`/`payouts`/`approvals` tabs for support, adds "Make Support"/"Revoke Support" buttons + purple Support badge; message_service overrides widened (SUPPORT + ORDER conversations readable/writable by staff) |
| 2026-04-20 | Admin audit log + dual-control payouts: `admin_audit_logs` + `payout_approvals` tables (migration `u7p8q9r0s1t2`); `AuditService` + `PayoutApprovalService`; `/admin/escrows/{id}/release` now returns `pending_second_approval` for amounts > `PAYOUT_APPROVAL_THRESHOLD_IQD` (default 500,000 IQD); new endpoints `/admin/payout-approvals/{pending,approve,reject}` + `/admin/audit-logs`; audit writes on user status change, admin promote/demote, escrow release request/release, payout approve/reject; admin UI: PayoutApprovalsTab + AuditLogTab (own-request blocked via requester-id check); in-process asyncio scheduler with Redis lock for daily marketplace_tasks (scheduler.py, hooked into lifespan) |
| 2026-04-20 | F1–F7 marketplace mechanics: BuyerRequest/Offer models + service + endpoints + frontend (/requests browse, /dashboard/requests client); Seller Levels (sellerlevel enum, 7 user columns, daily recalc task in marketplace_tasks.py); Order Requirements (pending_requirements GigOrderStatus, requirement_questions JSONB on gigs, requirement_answers + submit endpoint); Structured Delivery (gig_order_deliveries table, OrderDelivery model, auto-complete 3d task); Dispute model (disputes table, DisputeService, /disputes endpoints, co-exists with GigOrder dispute fields); Anti-offplatform filter (violation_logs table, MessageFilterService hooked into send_message, regex for email/phone/URL/external apps, escalation warning→block→24h suspend); Gig Ranking (rank_score Numeric on gigs, composite score computed daily in marketplace_tasks.py); migration chain o1j2k3l4m5n6→p2k3l4m5n6o1→q3l4m5n6o1p2→r4m5n6o1p2q3→s5n6o1p2q3r4 |
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
