# Kaasb — Engineering Handoff

> **Audience:** Senior software engineer joining the project to help close out launch-blocking issues and ship outstanding work.
> **Last updated:** 2026-04-25
> **Owner:** Dr. Mustafa Ghassan Abd (mustafaalnasiry21@gmail.com)
> **Phase:** Production live · public beta · launch-hardening in progress

---

## 1. What Kaasb is

Kaasb is an **Iraqi freelancing marketplace** — the local-market equivalent of Upwork/Fiverr, denominated in Iraqi Dinar (IQD) and built around a single Iraqi-only payment rail (Qi Card). The platform supports two parallel sales models:

1. **Job board** — clients post jobs, freelancers submit proposals, accepted proposals become contracts with milestones.
2. **Service catalog** ("services", historically "gigs") — freelancers publish fixed-price packaged offers; clients place orders directly. Renamed from "gig" → "service" / "خدمة" on 2026-04-21 (atomic migration `z2v3w4x5y6z7`).

Both models settle through the same escrow + payout system. Kaasb takes a **10% platform fee** on completed work.

The product is **Arabic-primary (RTL)** with English secondary. All translations are **inline ternaries** (`ar ? '...' : '...'`) — there is no `next-intl` or message-bundle system at runtime.

---

## 2. Stack at a glance

| Layer | Tech |
|---|---|
| Backend | FastAPI 0.136.0 · Python 3.12 · Uvicorn / Gunicorn |
| ORM | SQLAlchemy 2.0 (`Mapped` / `mapped_column`) · Alembic |
| Frontend | Next.js 15.5.15 (App Router) · React 19 · TypeScript 5.7 strict |
| Styling | Tailwind 3.4 · shadcn/ui |
| State | Zustand (auth) · React Query patterns via `src/lib/api.ts` axios |
| DB / Cache | PostgreSQL 16 · Redis 7 |
| Auth | JWT (httpOnly cookies, 30 min access + 7 day refresh) · Google OAuth · Facebook · Phone OTP (currently delivered via email — Twilio in roadmap) |
| Payments | **Qi Card v0 only** (IQD redirect flow). Stripe / Wise are fully removed. |
| Hosting | Hetzner CPX22 — `116.203.140.27` — kaasb.com |
| Monitoring | Prometheus + Grafana + Alertmanager (Discord + Gmail) · Sentry |
| CI/CD | GitHub Actions · GHCR images · `deploy.sh` over SSH |

SSH to prod: `ssh -i ~/.ssh/id_ed25519 deploy@116.203.140.27 -p 2222`

---

## 3. Architecture summary

### Backend — strict layering

```
HTTP request
  → api/v1/endpoints/*.py     (router; HTTP only — no SQL, no business logic)
    → services/*.py           (business logic; AsyncSession; raises domain exceptions)
      → models/*.py           (SQLAlchemy 2.0; lazy="raise" forces eager loading)
```

- Domain exceptions live in `core/exceptions.py` and are mapped to HTTP codes in `main.py`. Services **never raise `HTTPException` directly**.
- Pydantic v2 throughout (`model_dump`, `model_validate` — never `.dict()` or `.from_orm()`).
- Background work uses `asyncio.create_task()`. There is an **in-process scheduler with a Redis lock** for daily marketplace tasks (`scheduler.py`, hooked into FastAPI lifespan) — no Celery.
- Cross-worker WebSocket delivery uses **Redis pub/sub** (`psubscribe` pattern) — see `services/websocket_manager.py`.

### Frontend — Next.js App Router

- `src/app/` — pages (SSR for public/SEO pages, CSR for dashboards)
- `src/components/` — shared UI (shadcn/ui-based)
- **All API calls go through `src/lib/api.ts`** (axios). Domain-specific APIs live in `src/lib/api/{auth,users,jobs,services,...}.ts` and are re-exported through `api.ts`.
- Auth state in Zustand: `src/lib/auth-store.ts`.
- Edge middleware (`src/middleware.ts`) protects `/dashboard` and `/admin`, and 308-redirects deprecated `/gigs*` routes to `/services*`.
- i18n via `useLocale()` from `src/providers/locale-provider.tsx` (client) or `cookies()` (server). RTL via `dir="rtl"` at root.

### Auth flow

JWT access token (30 min) + refresh token (7 days, hashed in DB) — both in **httpOnly cookies**. `/auth/refresh` reads the refresh token from the cookie. Social login via `POST /auth/social`. Phone OTP via `/auth/phone/send-otp` + `/auth/phone/verify-otp`. Password change/reset revokes **all** live refresh tokens and bumps `users.token_version` (forced re-auth).

### Payments — manual-payout reality

Important: **Qi Card has no payout API in v0 or v1.** Confirmed against the full v1 3DS OpenAPI spec — only 4 endpoints exist: `POST /payment`, `GET /payment/{id}/status`, `POST /payment/{id}/cancel`, `POST /payment/{id}/refund`. The end-to-end money flow is:

1. Client pays via Qi Card (redirect flow, HMAC-signed return URL).
2. Funds land in **merchant account**; an `Escrow` row tracks the obligation logically.
3. Order/contract completes → escrow flips to `released`.
4. **Admin manually transfers** the freelancer's payout via the Qi Card merchant app to their `qi_card_phone` + `qi_card_holder_name` (both required before the Release button enables — see migration `y1u2v3w4x5y6`).
5. Admin clicks **Mark Paid** in Kaasb to record settlement.

Payouts above `PAYOUT_APPROVAL_THRESHOLD_IQD` (default **500,000 IQD**) require **dual-control** — a second admin approves before release. Refunds use the v0 API path that does not expose refunds; for now `refund_payment()` raises and refunds are processed manually in the merchant portal. Migrating to v1 3DS for refunds is tracked as Known Issue #2.

---

## 4. Core domain workflows

### 4a. Job → Proposal → Contract

```
Client posts job  ──▶  freelancers submit proposals  ──▶  client accepts proposal
   (jobs)               (proposals)                       (contract created)
                                                              │
                                                              ▼
                                                  milestones (submit/approve)
                                                              │
                                                              ▼
                                                escrow funded → released → fee + payout
                                                              │
                                                              ▼
                                                       reviews (both parties)
```

Jobs are **fixed-price only** — the hourly job type was removed on 2026-04-20 (migration `v8q9r0s1t2u3`).

### 4b. Service order

```
Freelancer publishes service  ──▶  admin approves  ──▶  client orders + answers requirement questions
                                                                         │
                                                                         ▼
                                                       order: pending_requirements → in_progress
                                                                         │
                                                                         ▼
                                                            structured delivery (message + files)
                                                                         │
                                                                         ▼
                                                client accepts (or 3-day auto-complete)
                                                                         │
                                                                         ▼
                                                       escrow released → fee + payout
```

Stale `pending` orders (no `funded` escrow within 30 min) are auto-cancelled by `expire_stale_pending_orders` and `Service.orders_count` is decremented.

### 4c. Disputes

A client or freelancer can raise a dispute on an order in any state up to and including `pending_requirements`. Dispute opens → escrow frozen → admin reviews evidence → admin resolves with **release** (to freelancer) or **refund** (to client). All dispute events generate system messages in the order chat. See `services/dispute_service.py`.

### 4d. Chat / messaging

Three conversation types: `USER` (freelancer ↔ client), `ORDER` (scoped to an order, admin can read/write for mediation), `SUPPORT` (any user ↔ admin/support staff). Messages support file attachments. An anti-off-platform filter (`MessageFilterService`) detects email/phone/URL/external-app strings; escalation is **warning → block → 24h chat suspension** with a `violation_logs` audit trail. Read receipts + typing indicators ship via WebSocket (Redis-backed presence).

### 4e. Buyer Requests (F1)

Clients post short-form buyer requests; freelancers send offers (optionally tied to an existing service). Accepted offers create a service order. See `models/buyer_request.py`.

---

## 5. Where things are — fast index

The full file index is in [`CLAUDE.md`](../CLAUDE.md) (the AI-assistant navigation map — read it once; it's the single best source of truth for "what file has what"). Highlights:

- **Backend models:** `backend/app/models/{user,job,proposal,contract,service,payment,message,notification,review,dispute,buyer_request,violation_log}.py`
- **Backend services:** `backend/app/services/{auth,user,job,proposal,contract,catalog,payment,admin,message,notification,review,dispute,email,qi_card_client}_service.py`
- **Backend endpoints:** `backend/app/api/v1/endpoints/*`
- **Frontend API layer:** `frontend/src/lib/api/*` (every HTTP call is here — start here when chasing a feature)
- **Frontend pages:** `frontend/src/app/**`
- **Migrations:** `backend/alembic/versions/` — **linear chain, 36 migrations**. Always `alembic upgrade head && alembic check` after generating one.

---

## 6. Progress tracker (high-level history)

Detailed line-by-line history is in `CLAUDE.md` under **Progress Tracker**. Compressed view:

| Period | What shipped |
|---|---|
| 2026-03-25 | Security audit (29 issues) + code-quality audit (20 issues) — all resolved. |
| 2026-04-05 | All 20 build checkpoints complete; **production goes live**. |
| 2026-04-10 → 13 | Post-launch fixes (Next.js CVE, auth store bugs, gig lifecycle hardening, admin promote/demote). |
| 2026-04-14 | WebSocket cross-worker via Redis pub/sub (Known Issue #1 closed). Service orders wired to Qi Card escrow (Issue #6 closed). Admin page + `api.ts` refactored. |
| 2026-04-15 | Active Sessions feature (per-device revoke). CI history cleaned, lockfile regenerated. |
| 2026-04-17 | Chat system Phase 1+2+3 — conversation types, system messages, read receipts, presence, typing indicators. |
| 2026-04-18 | Service image upload, hourly_rate fully removed, security CVE dep bumps, admin support inbox. |
| 2026-04-19 → 20 | Production-readiness hardening (HMAC, secure OTP, sanitize fix, dispute lifecycle, idempotency, atomic UPDATEs). Comprehensive enum normalization. F1–F7 marketplace mechanics (buyer requests, seller levels, order requirements, structured delivery, disputes, anti-off-platform filter, gig ranking). Admin audit log + dual-control payouts. SUPPORT role. |
| 2026-04-21 | **Atomic gig → service rename** across DB, code, URLs (308 redirect). Payout cardholder-name field. |
| 2026-04-22 | 12-PR cherry-pick onto post-rename main: payments hardening (P1–P4), notifications (N1–N4), chat (C1–C4). |
| 2026-04-22 | Gig-domain audit + 5 fix PRs (escrow release path fixes, stale-order expiry, dispute status, service rating mirroring, revision due-date reset). |
| 2026-04-23 | **Professional-launch plan Phases 1–8** executed: backup wiring, Discord alerts, runbooks (dispute/support/payout/refund), Playwright E2E + 6 backend integration test files, error budgets, SEO + JSON-LD, /help + /faq + /how-it-works, support macros. |
| 2026-04-24 | Switch-to-selling navbar toggle, language-switcher hang fix, password-reset email rewrite, logout 2-click fix, "sign out of all other devices", footer help links. Local Playwright dev loop live. |
| 2026-04-25 | Reviews aggregate filter fix (hidden reviews no longer skew avg). Migration chain collision fix. **Audit pass** — signup, reviews, images audits added under `docs/launch/`. **Nightly bug scan** (`docs/audits/nightly-2026-04-25.md`) — see §7. |

---

## 7. What's left — open work, by priority

This is the action list a new engineer should drive against. Items with file:line refs are concrete fixes; items in italics are research/sequencing decisions.

### P0 — fix before next release

These four items came out of the 2026-04-25 nightly audit (full report: [`docs/audits/nightly-2026-04-25.md`](audits/nightly-2026-04-25.md)).

1. **Admin lockout possible via `update_user_status`.** [`backend/app/services/admin_service.py:194-208`](../backend/app/services/admin_service.py#L194-L208). The last-admin guard only runs in `toggle_superuser`; `update_user_status` lets a single admin suspend/deactivate every other admin (including themselves). **Fix:** add `acting_admin` parameter, self-target guard, and a last-active-admin check on every path that drops an admin out of the active pool.
2. **Last-admin check race.** [`backend/app/services/admin_service.py:222-232`](../backend/app/services/admin_service.py#L222-L232). The `is_superuser AND status=ACTIVE` count has no `FOR UPDATE`; two admins concurrently demoting each other both pass and commit. **Fix:** add `with_for_update()` on the admin rows or use a unique-row lock pattern.
3. **Payout dual-control bypass via splitting.** [`backend/app/services/payout_approval_service.py:74-97`](../backend/app/services/payout_approval_service.py#L74-L97). Threshold check is per-escrow-row only; an admin controlling multiple sub-threshold escrows for the same freelancer can release unlimited totals without a second approver. **Fix:** aggregate per payee per rolling window.
4. **Audit-log loss race on admin mutations.** [`backend/app/api/v1/endpoints/admin.py:107-115`](../backend/app/api/v1/endpoints/admin.py#L107-L115). The handler commits the mutation, *then* writes the audit row and commits again. If the audit write fails the status change is permanent with no trail. Same shape in `toggle_admin`, `toggle_support`, `unsuspend_chat`. **Fix:** either single-transaction commit or post-mutation outbox.

### P1 — high (this week)

- **Bump axios to ^1.15.2** (`frontend/package.json`). Three high-severity CVEs cluster (SSRF, cloud-metadata exfil, DoS). Non-major bump. *Trivial.*
- **Add audit row on `PUT /admin/jobs/{id}/status`.** [`backend/app/api/v1/endpoints/admin.py:235-248`](../backend/app/api/v1/endpoints/admin.py#L235-L248). Job moderation is currently silent in the audit trail.
- **Harden free-form status enum coercion.** `update_user_status`, `update_job_status`, `list_users` accept `new_status: str` and call `Enum(value)` with no try/except → invalid value surfaces as a raw 500 `ValueError`. Convert to `BadRequestError`.
- **Service orders have no review path** (launch blocker — see [`docs/launch/reviews-audit.md`](launch/reviews-audit.md)). Reviews today only live on contracts; service-style sellers show 0 reviews forever. Decide schema (extend `reviews.contract_id` to be either contract or order, or add `service_order_id` column) and ship.
- **Migrate admin.ts from `/gigs/admin/*` to `/services/admin/*`.** [`frontend/src/lib/api/admin.ts`](../frontend/src/lib/api/admin.ts). Required before the deprecated `/gigs` alias router is dropped in Phase 2.
- **Audit-service exception swallowing.** [`backend/app/services/audit_service.py:50-77`](../backend/app/services/audit_service.py#L50-L77) flushes inside the caller's `db` session and swallows; a flush failure can leave the session partially failed and silently lose the underlying admin action.
- **Approve-action `is_superuser` re-check.** [`backend/app/services/payout_approval_service.py:153-200`](../backend/app/services/payout_approval_service.py#L153-L200). Route dependency catches it today, but the service has no defense-in-depth — re-verify at decision time.
- **Phone OTP via Twilio.** Currently OTP is delivered via email (beta workaround). To go live: set `TWILIO_*` env vars and switch `email_service.send_phone_otp` → Twilio in `auth_service.send_phone_otp`. Known Issue #4.

### P2 — medium

- **Paginate `list_funded_escrows`.** [`backend/app/services/admin_service.py:354-420`](../backend/app/services/admin_service.py#L354-L420). Returns full freelancer email + phone + Qi Card details for every funded escrow with no cap → leaked admin cookie = full payout-PII scrape.
- **Decimal consistency for IQD amounts.** [`backend/app/services/payout_approval_service.py:71-72`](../backend/app/services/payout_approval_service.py#L71-L72) casts to `float`. Fine today, silent precision boundary at scale.
- **Pending-escrow sum missing currency filter.** [`backend/app/services/admin_service.py:107-111`](../backend/app/services/admin_service.py#L107-L111) sums across currencies if data drift introduces non-IQD rows.
- **Split audit-log endpoint scope.** [`backend/app/api/v1/endpoints/admin.py:441-487`](../backend/app/api/v1/endpoints/admin.py#L441-L487). Currently gated on `get_current_staff` (support included); support staff should not read `escrow_release` / `payout_approved` / `user_promoted_admin` entries.
- **Idempotency on `mark_payout_paid`.** Double-click can record two settlement entries — needs an idempotency key.
- **Server-side image resizing + EXIF strip + crop UI.** Multi-MB phone uploads currently served 1:1 to 32px avatars. See [`docs/launch/images-audit.md`](launch/images-audit.md).

### P3 — low / cleanup

- 3 `ruff` autofixes in `backend/app/models/review.py` + `backend/app/services/catalog_service.py`.
- 27 unused type exports across `frontend/src/types/*` — delete as you touch them.
- 5 ESLint warnings (mostly `<img>` → `<Image>` migrations + 2 unused imports).
- 19 English-only strings, mostly in legal pages — confirm with owner whether legal copy needs Arabic mirroring.
- Native `confirm()` on critical admin actions ([`frontend/src/app/admin/page.tsx:241-247`](../frontend/src/app/admin/page.tsx#L241-L247)) — replace with RTL-aware modal.
- Polling without visibility-pause in payout-approvals tab ([line 54-60](../frontend/src/app/admin/tabs/payout-approvals-tab.tsx#L54-L60)).

### Standing known issues (non-blocking, scoped on roadmap)

| # | Issue | Notes |
|---|---|---|
| 2 | Qi Card v0 has no refund endpoint | Migrate to v1 3DS API (`uat-sandbox-3ds-api.qi.iq`); needs merchant provisioning + `QI_CARD_V1_HOST` + `QI_CARD_TERMINAL_ID` + Basic-auth creds + persisting v1 paymentId at create time. Until then refunds are manual via merchant portal. |
| 3 | No payout API in either Qi Card v0 or v1 3DS | Confirmed against full OpenAPI spec — only 4 endpoints. **Manual payout via merchant app is the design**, not a workaround. |
| 7 | `src/messages/{ar,en}.json` exist but are unused | All translations are inline ternaries. Decide: delete the files, or migrate to a real i18n runtime. |

### Pending operational items (need user input, not code)

- **Qi Card merchant portal walkthrough** is pending — payout + refund admin runbooks ([`docs/admin/payout-runbook.md`](admin/payout-runbook.md), [`docs/admin/refund-runbook.md`](admin/refund-runbook.md)) have `[PENDING QICARD PORTAL WALKTHROUGH]` placeholders. 19 specific questions are queued in the project-internal note `project_pending_qicard_walkthrough.md`.

---

## 8. Quality bars (continuous, not phase-gated)

These are not work items — they're standing bars every PR is held to. Drawn from the launch decision log.

- **Security** — no new CVEs, secrets in env only, all admin actions audited, dual-control on high-value money moves.
- **SEO** — every public page has `generateMetadata` + JSON-LD, sitemap maintained, OG image present.
- **i18n / RTL** — every user-visible string has `ar ? ... : ...`. RTL-tested in real Arabic locale.
- **Mobile** — tested on a real phone in both orientations before merge for any UI change. Mobile-app cross-platform port is on the roadmap *after* web launch — keep API stable, no web-only UX decisions.
- **Tests** — Playwright smoke against live kaasb.com on push-to-main; backend integration tests under `backend/tests/integration/` (template: `test_service_order_placement.py`).

---

## 9. How to get set up

```bash
# Clone
git clone <repo>
cd kaasb

# Backend (Python 3.12)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # populate DB / Redis / Qi Card sandbox creds
alembic upgrade head
python scripts/seed_categories.py
uvicorn app.main:app --reload --port 8000

# Frontend (Node 22)
cd frontend
npm ci --legacy-peer-deps
cp .env.example .env.local
npm run dev   # http://localhost:3000

# Or all-in-one
docker compose up -d

# First admin
cd backend && python scripts/create_admin.py
```

Before any PR:

```bash
cd backend && ruff check app/ && mypy app/ && pytest
cd frontend && npm run build && npm run type-check && npm run lint
cd backend && alembic check
```

---

## 10. Operations quick reference

| Action | Command |
|---|---|
| Full prod redeploy | `./deploy.sh full` |
| Pull + restart only | `./deploy.sh --pull` |
| Migrations only | `./deploy.sh --migrate` |
| Roll back to previous image | `./deploy.sh --rollback` |
| Manual backup | `./deploy.sh --backup` |
| Status / health | `./deploy.sh --status` |
| Tail all logs | `./deploy.sh --logs` |
| Grafana (SSH tunnel) | `ssh -L 3001:localhost:3001 deploy@116.203.140.27 -p 2222 -N` then http://localhost:3001 |

---

## 11. Where to read more

| Topic | File |
|---|---|
| Authoritative file index, conventions, env vars, migration chain | [`CLAUDE.md`](../CLAUDE.md) |
| Full architecture deep-dive | [`docs/architecture.md`](architecture.md) |
| Deployment | [`docs/deployment-guide.md`](deployment-guide.md) |
| Disaster recovery | [`docs/disaster-recovery.md`](disaster-recovery.md) |
| Operations quickstart | [`docs/launch/ops-quickstart.md`](launch/ops-quickstart.md) |
| Launch decision log + checklist | [`docs/launch/decision-log.md`](launch/decision-log.md), [`docs/launch/go-no-go-checklist.md`](launch/go-no-go-checklist.md) |
| Error budgets | [`docs/launch/error-budgets.md`](launch/error-budgets.md) |
| Domain audits | [`docs/launch/{signup,reviews,images,support-dispute,chat-notifications}-audit.md`](launch/) |
| Latest nightly bug scan | [`docs/audits/nightly-2026-04-25.md`](audits/nightly-2026-04-25.md) |
| Admin runbooks | [`docs/admin/{dispute,support,payout,refund}-runbook.md`](admin/) |
| Support macros (canned responses) | [`docs/admin/support-macros.md`](admin/support-macros.md) |
| Qi Card v1 migration plan | [`docs/launch/phase-4-qicard-v1.md`](launch/phase-4-qicard-v1.md) |
| Fiverr-parity research | [`docs/launch/fiverr-parity-notes.md`](launch/fiverr-parity-notes.md) |
| API reference | [`docs/api-reference.md`](api-reference.md) |
| Git workflow + commit conventions | [`docs/git-workflow.md`](git-workflow.md) |

---

## 12. Contact

- **Owner / product decisions:** Dr. Mustafa Ghassan Abd — mustafaalnasiry21@gmail.com
- **Repo:** see `GITHUB_REPO` env var
- **Production server:** `deploy@116.203.140.27` (port 2222) — SSH key required, request from owner
- **Domain:** kaasb.com

When in doubt, the order to read is: **this file → `CLAUDE.md` → the relevant audit doc in `docs/launch/` or `docs/audits/` → the code.**
