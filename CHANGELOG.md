# Changelog

All notable API changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [1.0.0] — 2026-03-27

Initial production release of the Kaasb API.

### Added

#### Authentication (`/api/v1/auth/`)
- `POST /auth/register` — User registration with JWT token response
- `POST /auth/login` — Email/password login
- `POST /auth/refresh` — Token refresh with rotation
- `GET /auth/me` — Authenticated user profile
- `POST /auth/logout` — Revoke current refresh token
- `POST /auth/logout-all` — Revoke all refresh tokens (all devices)

#### Users (`/api/v1/users/`)
- `GET /users/freelancers` — Search/browse freelancers with filtering
- `GET /users/profile/{username}` — Public user profile
- `PUT /users/profile` — Update own profile
- `POST /users/avatar` — Upload avatar image (JPEG/PNG/WebP, max 10 MB)
- `DELETE /users/avatar` — Remove avatar
- `PUT /users/password` — Change password
- `DELETE /users/account` — Deactivate account (soft delete)

#### Jobs (`/api/v1/jobs/`)
- `GET /jobs` — Browse and search job postings (public)
- `POST /jobs` — Create a job posting (client role)
- `GET /jobs/my/posted` — List own job postings
- `GET /jobs/{job_id}` — Get job details (public)
- `PUT /jobs/{job_id}` — Update job posting (owner only)
- `POST /jobs/{job_id}/close` — Close job to new proposals
- `DELETE /jobs/{job_id}` — Delete job (no active contract)

#### Proposals (`/api/v1/proposals/`)
- `POST /proposals/jobs/{job_id}` — Submit proposal (freelancer role)
- `GET /proposals/my` — List own proposals
- `GET /proposals/jobs/{job_id}/list` — List proposals on a job (owner only)
- `GET /proposals/{proposal_id}` — Get proposal details
- `PUT /proposals/{proposal_id}` — Update pending proposal
- `POST /proposals/{proposal_id}/withdraw` — Withdraw proposal
- `POST /proposals/{proposal_id}/respond` — Accept/shortlist/reject (client only)

#### Contracts & Milestones (`/api/v1/contracts/`)
- `GET /contracts/my` — List own contracts
- `GET /contracts/{contract_id}` — Get contract details
- `POST /contracts/{contract_id}/milestones` — Add milestones to contract
- `PUT /contracts/milestones/{milestone_id}` — Update pending milestone
- `DELETE /contracts/milestones/{milestone_id}` — Delete pending milestone
- `POST /contracts/milestones/{milestone_id}/start` — Start milestone (freelancer)
- `POST /contracts/milestones/{milestone_id}/submit` — Submit for review (freelancer)
- `POST /contracts/milestones/{milestone_id}/review` — Approve/request-changes (client)

#### Payments (`/api/v1/payments/`)
- `GET /payments/summary` — Payment dashboard summary
- `GET /payments/accounts` — List payment accounts
- `POST /payments/accounts` — Setup payment account (Stripe/Qi Card)
- `GET /payments/transactions` — List transactions
- `POST /payments/escrow/fund` — Fund milestone escrow
- `POST /payments/payout` — Request payout (Wise/Qi Card)
- `POST /payments/qi-card/webhook` — Qi Card webhook receiver

#### Reviews (`/api/v1/reviews/`)
- `GET /reviews/user/{user_id}` — Get user reviews
- `GET /reviews/user/{user_id}/stats` — Review statistics
- `GET /reviews/contract/{contract_id}` — Reviews for a contract
- `POST /reviews/contract/{contract_id}` — Submit review (post-contract)

#### Messages (`/api/v1/messages/`)
- `GET /messages/conversations` — List conversations
- `POST /messages/conversations` — Start new conversation
- `GET /messages/conversations/{id}` — Get conversation messages
- `POST /messages/conversations/{id}` — Send message

#### Notifications (`/api/v1/notifications/`)
- `GET /notifications` — Get notifications
- `GET /notifications/unread-count` — Unread notification count
- `POST /notifications/mark-read` — Mark specific notifications read
- `POST /notifications/mark-all-read` — Mark all notifications read

#### Admin (`/api/v1/admin/`)
- `GET /admin/stats` — Platform-wide statistics
- `GET /admin/users` — List all users
- `PUT /admin/users/{id}/status` — Update user status
- `POST /admin/users/{id}/toggle-admin` — Toggle admin privileges
- `GET /admin/jobs` — List all jobs
- `PUT /admin/jobs/{id}/status` — Update job status
- `GET /admin/transactions` — List all transactions

#### Health (`/api/v1/health/`)
- `GET /health` — Liveness check (DB + Redis)
- `GET /health/ready` — Readiness probe (migrations applied)
- `GET /health/detailed` — Full diagnostics (bearer token protected)

#### Infrastructure
- WebSocket endpoint `GET /api/v1/ws?token=<jwt>` — Real-time notifications
- `GET /metrics` — Prometheus metrics endpoint
- JWT authentication with refresh token rotation
- Redis-backed rate limiting with in-memory fallback
- CSRF protection for state-changing requests
- Sentry error tracking with PII scrubbing
- Prometheus + Grafana monitoring stack
- Qi Card (IQD) + Stripe (USD) + Wise (payouts) payment stack

### Security
- Passwords: bcrypt hashing, complexity requirements enforced
- JWT: HS256, 30-min access tokens, 7-day refresh tokens with rotation
- `token_version` field invalidates tokens on password change
- Rate limiting: 5/5min login, 3/10min register, 120/min standard API
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options

---

## Versioning Policy

- **Major** (v2.0.0): Breaking API changes (field removals, endpoint renames, auth changes)
- **Minor** (v1.1.0): New endpoints, new optional fields, new capabilities
- **Patch** (v1.0.1): Bug fixes, documentation updates, performance improvements

Breaking changes announced **6 months** in advance via:
- `X-Deprecated: true` response header on affected endpoints
- `X-Sunset-Date: YYYY-MM-DD` response header
- GitHub release notes

[Unreleased]: https://github.com/mustafaalrasheed/kaasb/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mustafaalrasheed/kaasb/releases/tag/v1.0.0
