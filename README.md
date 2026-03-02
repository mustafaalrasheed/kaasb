# Kaasb — Freelancing Platform

A full-stack freelancing marketplace connecting clients with freelancers through structured job postings, milestone-based contracts, and integrated escrow payments.

**Version**: 1.0.0 &nbsp;|&nbsp; **Tests**: 26/26 passing &nbsp;|&nbsp; **Branch**: `main`

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Environment Variables](#environment-variables)
6. [API Reference](#api-reference)
7. [Database Schema](#database-schema)
8. [Security](#security)
9. [Testing](#testing)
10. [Production Deployment](#production-deployment)
11. [Project Structure](#project-structure)

---

## Overview

Kaasb is a platform built for the Iraqi freelance market, with dual payment support via Stripe (global clients) and Wise (local freelancer payouts). It supports the full lifecycle of freelance work:

```
Client posts job → Freelancer submits proposal → Client accepts → Contract created
→ Client adds milestones → Freelancer works → Submits for review
→ Client approves → Escrow released → Payout to freelancer
```

**Core capabilities:**

- Dual-role user accounts (client, freelancer, admin)
- Job marketplace with full-text search and filtering
- Competitive proposal and bidding system
- Milestone-based contracts with escrow protection
- Stripe + Wise payment integration
- 5-star review system with category ratings
- Real-time in-app notifications
- Direct messaging between users
- Admin dashboard for platform moderation

---

## Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Framework | FastAPI | 0.115.6 |
| Server (dev) | Uvicorn | 0.34.0 |
| Server (prod) | Gunicorn | 21.2.0 |
| Language | Python | 3.12 |
| ORM | SQLAlchemy (async) | 2.0.36 |
| Database driver | asyncpg | 0.30.0 |
| Validation | Pydantic v2 | 2.10.3 |
| Auth | Python-Jose + Passlib | 3.3.0 / 1.7.4 |
| Migrations | Alembic | 1.14.0 |
| Payments | Stripe SDK | 7.12.0 |
| Image processing | Pillow | 11.0.0 |
| Testing | pytest + pytest-asyncio | 8.3.4 |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 15.1.0 |
| UI Library | React | 19.0.0 |
| Language | TypeScript | 5.7.2 |
| Styling | Tailwind CSS | 3.4.17 |
| State management | Zustand | 5.0.2 |
| HTTP client | Axios | 1.7.9 |
| Forms | React Hook Form + Zod | 7.54.2 / 3.24.1 |
| Icons | Lucide React | 0.468.0 |
| Toasts | Sonner | 1.7.1 |
| Date utilities | date-fns | 4.1.0 |

### Infrastructure

| Component | Technology |
|---|---|
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Reverse proxy | Nginx (production) |
| Containerization | Docker + Docker Compose |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Browser                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────────────┐
│                    Nginx  (production only)                  │
│              Port 80/443  →  Reverse proxy                  │
└──────────┬──────────────────────────────┬───────────────────┘
           │ /api/*                       │ /*
┌──────────▼──────────┐       ┌───────────▼────────────┐
│   FastAPI Backend   │       │   Next.js Frontend     │
│   Port 8000         │       │   Port 3000            │
│                     │       │   App Router + SSR     │
│  Rate Limiter       │       └────────────────────────┘
│  Security Headers   │
│  JWT Auth           │       ┌────────────────────────┐
│                     │◄─────►│   PostgreSQL 16        │
│  /auth              │       │   Port 5432            │
│  /users             │       └────────────────────────┘
│  /jobs              │
│  /proposals         │       ┌────────────────────────┐
│  /contracts         │◄─────►│   Redis 7              │
│  /payments          │       │   Port 6379            │
│  /reviews           │       └────────────────────────┘
│  /messages          │
│  /notifications     │       ┌────────────────────────┐
│  /admin             │◄─────►│   Stripe / Wise APIs   │
└─────────────────────┘       └────────────────────────┘
```

Every request passes through two middleware layers before reaching the route handler:

1. **`RateLimitMiddleware`** — Sliding-window rate limiting per IP and endpoint tier
2. **`SecurityHeadersMiddleware`** — Attaches security headers and a per-request trace ID

Route handlers delegate to a **Service** class (e.g. `ContractService`) which encapsulates all business logic and interacts with the database via SQLAlchemy async sessions.

---

## Quick Start

### Prerequisites

- Docker Desktop (with Docker Compose v2)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/mustafaalrasheed/kaasb.git
cd kaasb
```

### 2. Start all services

```bash
docker compose up --build
```

This starts four containers:

| Container | Service | Port |
|---|---|---|
| `kaasb_db` | PostgreSQL 16 | 5432 |
| `kaasb_redis` | Redis 7 | 6379 |
| `kaasb_backend` | FastAPI (uvicorn, hot-reload) | 8000 |
| `kaasb_frontend` | Next.js (hot-reload) | 3000 |

The backend runs `create_all()` on startup — no manual migration step is needed for a fresh install.

### 3. Open the app

| URL | Description |
|---|---|
| `http://localhost:3000` | Frontend |
| `http://localhost:8000/docs` | Interactive API docs (Swagger UI) |
| `http://localhost:8000/redoc` | API docs (ReDoc) |
| `http://localhost:8000/health` | Health check |

### 4. Create an admin user (optional)

```bash
docker exec -it kaasb_backend python -m scripts.create_admin \
  --email admin@example.com \
  --username admin \
  --password "SecurePass123!"
```

### Override settings

To override any backend setting, create `backend/.env`:

```env
SECRET_KEY=change-this-in-production
STRIPE_SECRET_KEY=sk_test_...
WISE_API_KEY=...
```

---

## Environment Variables

### Backend (`backend/.env`)

#### Application

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Kaasb` | Application name |
| `APP_VERSION` | `0.1.0` | API version string |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `True` | Enable debug mode |
| `API_PREFIX` | `/api/v1` | Base path for all API routes |

#### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | *(set by compose)* | Async PostgreSQL URL (`postgresql+asyncpg://...`) |

#### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

#### Authentication

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(change in production)* | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

#### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins (JSON array) |

#### File Uploads

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum file upload size |
| `ALLOWED_IMAGE_TYPES` | `jpeg,png,webp` | Accepted MIME types |
| `UPLOAD_DIR` | `uploads` | Directory for uploaded files |

#### Platform

| Variable | Default | Description |
|---|---|---|
| `PLATFORM_FEE_PERCENT` | `10.0` | Platform fee taken from each milestone payment |
| `MIN_HOURLY_RATE` | `5.0` | Minimum freelancer hourly rate (USD) |
| `MAX_HOURLY_RATE` | `500.0` | Maximum freelancer hourly rate (USD) |

#### Stripe

| Variable | Default | Description |
|---|---|---|
| `STRIPE_SECRET_KEY` | *(empty)* | `sk_live_...` or `sk_test_...` |
| `STRIPE_PUBLISHABLE_KEY` | *(empty)* | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | *(empty)* | Webhook endpoint secret |

#### Wise (Payouts)

| Variable | Default | Description |
|---|---|---|
| `WISE_API_KEY` | *(empty)* | Wise API token |
| `WISE_PROFILE_ID` | *(empty)* | Wise business profile ID |
| `WISE_ENVIRONMENT` | `sandbox` | `sandbox` \| `production` |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

---

### Authentication

#### `POST /auth/register`

Register a new user. Returns JWT tokens immediately on success.

**Body**
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "primary_role": "client"
}
```

`primary_role`: `client` | `freelancer` | `admin`

Password requirements: minimum 8 characters, at least one uppercase letter, one digit, and one special character.

**Rate limit**: 3 registrations per 10 minutes per IP.

---

#### `POST /auth/login`

Authenticate and receive tokens.

**Body**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Rate limit**: 5 attempts per 5 minutes per IP.

---

#### `POST /auth/refresh`

Exchange a refresh token for a new access token.

**Body**
```json
{ "refresh_token": "..." }
```

---

#### `GET /auth/me` *(Auth required)*

Returns the authenticated user's full profile.

---

### Users

#### `GET /users/freelancers`

Browse freelancers.

**Query params**

| Param | Type | Description |
|---|---|---|
| `skills` | string | Comma-separated skill tags |
| `min_rate` | float | Minimum hourly rate |
| `max_rate` | float | Maximum hourly rate |
| `experience_level` | string | `entry` \| `intermediate` \| `expert` |
| `country` | string | Country name |
| `sort` | string | `rating` \| `rate_asc` \| `rate_desc` \| `jobs_completed` |
| `page` / `page_size` | int | Pagination (default: 1 / 20, max page_size: 50) |

---

#### `GET /users/profile/{username}`

Public profile for any user.

---

#### `PUT /users/profile` *(Auth required)*

Update own profile. All fields are optional (partial update).

**Body**
```json
{
  "first_name": "John",
  "bio": "Senior Python developer",
  "hourly_rate": 75.0,
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "country": "Iraq",
  "city": "Baghdad"
}
```

---

#### `POST /users/avatar` *(Auth required)*

Upload a profile avatar. `multipart/form-data`, field name: `file`.
Accepted types: JPEG, PNG, WebP. Max size: 10 MB.

---

#### `DELETE /users/avatar` *(Auth required)*

Remove the current avatar.

---

#### `PUT /users/password` *(Auth required)*

Change password.

**Body**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456@"
}
```

---

#### `DELETE /users/account` *(Auth required)*

Soft-deactivate the account.

---

### Jobs

#### `GET /jobs`

Browse job listings.

**Query params**

| Param | Type | Description |
|---|---|---|
| `category` | string | Job category |
| `job_type` | string | `fixed` \| `hourly` |
| `skills` | string | Comma-separated required skills |
| `min_budget` / `max_budget` | float | Budget range |
| `duration` | string | `less_than_week` \| `one_to_four_weeks` \| `one_to_three_months` \| `more_than_three_months` |
| `experience_level` | string | `entry` \| `intermediate` \| `expert` |
| `q` | string | Full-text search across title and description |
| `sort` | string | `newest` \| `budget_high` \| `budget_low` \| `proposals_low` |
| `page` / `page_size` | int | Pagination |

---

#### `POST /jobs` *(Client role required)*

Create a new job posting.

**Body**
```json
{
  "title": "Build a FastAPI Backend",
  "description": "We need a senior developer...",
  "category": "Web Development",
  "job_type": "fixed",
  "fixed_price": 1500.00,
  "skills_required": ["Python", "FastAPI", "Docker"],
  "experience_level": "intermediate",
  "duration": "one_to_four_weeks",
  "deadline": "2025-06-01T00:00:00Z"
}
```

---

#### `GET /jobs/my/posted` *(Client role required)*

List jobs posted by the authenticated client.

---

#### `GET /jobs/{job_id}`

Full job details including client info and proposal count.

---

#### `PUT /jobs/{job_id}` *(Owner only)*

Update a draft or open job. Same fields as creation, all optional.

---

#### `POST /jobs/{job_id}/close` *(Owner only)*

Close a job to new proposals.

---

#### `DELETE /jobs/{job_id}` *(Owner only)*

Delete a job. Only allowed if no proposal has been accepted.

---

### Proposals

#### `GET /proposals/my` *(Freelancer role required)*

All proposals submitted by the authenticated freelancer.

---

#### `POST /proposals/jobs/{job_id}` *(Freelancer role required)*

Submit a proposal on a job.

**Body**
```json
{
  "cover_letter": "I have 5 years of experience...",
  "bid_amount": 1200.00,
  "estimated_duration": "3 weeks"
}
```

One proposal per freelancer per job. Duplicates return `409 Conflict`.

---

#### `GET /proposals/jobs/{job_id}/list` *(Client, own jobs only)*

All proposals received on a job.

---

#### `GET /proposals/{proposal_id}`

Proposal details. Accessible by the job owner or the proposing freelancer.

---

#### `PUT /proposals/{proposal_id}` *(Proposing freelancer only)*

Update a pending proposal.

---

#### `POST /proposals/{proposal_id}/withdraw` *(Proposing freelancer only)*

Withdraw a pending or shortlisted proposal.

---

#### `POST /proposals/{proposal_id}/respond` *(Client, own jobs only)*

Respond to a proposal.

**Body**
```json
{
  "action": "accept",
  "client_note": "Looking forward to working with you!"
}
```

`action`: `shortlist` | `accept` | `reject`

Accepting a proposal automatically:
- Creates a contract linked to the job and proposal
- Sets the job status to `in_progress`
- Assigns the freelancer to the job
- Rejects all other pending proposals on the same job

---

### Contracts & Milestones

#### `GET /contracts/my` *(Auth required)*

All contracts where the user is client or freelancer.

**Query params**: `status`, `page`, `page_size`

---

#### `GET /contracts/{contract_id}` *(Auth required)*

Full contract detail with all milestones sorted by order. Accessible only by the client or freelancer on the contract.

---

#### `POST /contracts/{contract_id}/milestones` *(Client only)*

Add milestones to an active contract. The sum of all milestone amounts cannot exceed the contract total.

**Body**
```json
{
  "milestones": [
    {
      "title": "Project Setup",
      "description": "Docker, CI/CD, initial architecture",
      "amount": 300.00,
      "due_date": "2025-05-15T00:00:00Z",
      "order": 1
    },
    {
      "title": "Core Features",
      "amount": 900.00,
      "order": 2
    }
  ]
}
```

---

#### `PUT /contracts/milestones/{milestone_id}` *(Client only)*

Update a pending milestone's title, description, amount, or due date.

---

#### `DELETE /contracts/milestones/{milestone_id}` *(Client only)*

Delete a pending milestone.

---

#### `POST /contracts/milestones/{milestone_id}/start` *(Freelancer only)*

Mark a pending milestone as in-progress.

---

#### `POST /contracts/milestones/{milestone_id}/submit` *(Freelancer only)*

Submit a milestone for client review.

**Body**
```json
{ "submission_note": "Completed as per requirements. PR: https://..." }
```

---

#### `POST /contracts/milestones/{milestone_id}/review` *(Client only)*

Approve the submission or request a revision.

**Body**
```json
{
  "action": "approve",
  "feedback": "Excellent work!"
}
```

`action`: `approve` | `request_revision`

On approval:
- Milestone status changes to `paid`
- Escrowed funds are released to the freelancer (minus platform fee)
- Contract `amount_paid` is updated
- If all milestones are paid, contract status changes to `completed`

---

### Payments

#### `GET /payments/summary` *(Auth required)*

Dashboard summary: total spent/earned, active escrow balance, account count.

---

#### `GET /payments/accounts` *(Auth required)*

List the user's payment accounts.

---

#### `POST /payments/accounts` *(Auth required)*

Set up a payment account.

**Body — Stripe (clients)**
```json
{
  "provider": "stripe",
  "external_account_id": "cus_abc123"
}
```

**Body — Wise (freelancers)**
```json
{
  "provider": "wise",
  "wise_email": "freelancer@example.com",
  "wise_currency": "IQD"
}
```

---

#### `GET /payments/transactions` *(Auth required)*

Transaction history. Optional filter: `?type=escrow_fund|escrow_release|payout|...`

---

#### `POST /payments/escrow/fund` *(Client only)*

Fund the escrow for a specific milestone.

**Body**
```json
{ "milestone_id": "uuid" }
```

The platform fee (10%) is calculated and recorded. The net amount is held in escrow until the milestone is approved.

---

#### `POST /payments/payout` *(Freelancer only)*

Request a payout of available earnings to the configured Wise account.

---

### Reviews

#### `GET /reviews/user/{user_id}`

Public: all reviews for a user. Paginated.

---

#### `GET /reviews/user/{user_id}/stats`

Public: aggregated rating stats — average, total count, per-star distribution.

---

#### `GET /reviews/contract/{contract_id}`

Reviews attached to a specific contract.

---

#### `POST /reviews/contract/{contract_id}` *(Auth required)*

Submit a review for the other party on a completed contract. One review per party per contract.

**Body**
```json
{
  "rating": 5,
  "comment": "Excellent communication and delivered on time.",
  "communication_rating": 5,
  "quality_rating": 5,
  "professionalism_rating": 5,
  "timeliness_rating": 4
}
```

The contract must have `completed` status. Self-reviews are rejected.

---

### Notifications

#### `GET /notifications` *(Auth required)*

Paginated notification list. Query params: `unread_only=true`, `page`, `page_size`.

---

#### `GET /notifications/unread-count` *(Auth required)*

Returns `{ "count": N }`.

---

#### `POST /notifications/mark-read` *(Auth required)*

Mark specific notifications as read.

**Body**
```json
{ "notification_ids": ["uuid1", "uuid2"] }
```

---

#### `POST /notifications/mark-all-read` *(Auth required)*

Mark all notifications as read.

---

### Messages

#### `GET /messages/conversations` *(Auth required)*

List all conversations. Unread counts are calculated from the user's perspective.

---

#### `POST /messages/conversations` *(Auth required)*

Start a new conversation with another user.

**Body**
```json
{
  "recipient_id": "uuid",
  "initial_message": "Hi, I wanted to discuss the project.",
  "job_id": "uuid (optional)"
}
```

Self-messaging returns `400`. Existing conversations between the same two users (on the same job) are reused.

---

#### `GET /messages/conversations/{conversation_id}` *(Auth required)*

Fetch messages in a conversation. Auto-marks messages as read. Paginated.

---

#### `POST /messages/conversations/{conversation_id}` *(Auth required)*

Send a message.

**Body**
```json
{ "content": "Here is my update..." }
```

---

### Admin

All admin endpoints require `is_superuser = true`. Regular users receive `403 Forbidden`.

---

#### `GET /admin/stats`

Platform-wide statistics: user counts by role, active jobs, contracts, total revenue.

---

#### `GET /admin/users`

All users. Query params: `role`, `status`, `search` (username/email), `page`, `page_size`.

---

#### `PUT /admin/users/{user_id}/status`

Update a user's account status.

**Body**
```json
{ "status": "suspended", "reason": "Terms of service violation" }
```

`status`: `active` | `suspended` | `deactivated`

---

#### `POST /admin/users/{user_id}/toggle-admin`

Grant or revoke superuser privileges.

---

#### `GET /admin/jobs`

All jobs for moderation. Filterable by status.

---

#### `PUT /admin/jobs/{job_id}/status`

Override a job's status.

---

#### `GET /admin/transactions`

All platform transactions. Filterable by `type` and `status`.

---

## Database Schema

### Entities and Relationships

```
User ──< Job ──< Proposal >── User
              │
              └──> Contract ──< Milestone ──> Escrow
                       │
                       └──> Review

User ──< PaymentAccount
User ──< Transaction
User ──< Notification
User >──< Conversation ──< Message
```

### Milestone Lifecycle

```
PENDING ──> IN_PROGRESS ──> SUBMITTED ──┬──> APPROVED ──> PAID
               ^                         └──> REVISION_REQUESTED ──┘
               └─────────────────────────────────────────────────────
```

### Contract Status Flow

```
ACTIVE ──┬──> COMPLETED  (all milestones reach PAID status)
         ├──> CANCELLED
         ├──> DISPUTED
         └──> PAUSED
```

### Key Tables

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | Accounts for all roles | `email` unique, `username` unique |
| `jobs` | Job postings | Indexed on `title`, `category`, `status`, `client_id` |
| `proposals` | Freelancer bids on jobs | `UNIQUE(job_id, freelancer_id)` |
| `contracts` | Active work agreements | `UNIQUE(proposal_id)` |
| `milestones` | Deliverable phases of a contract | Ordered within contract |
| `escrows` | Held funds per milestone | `UNIQUE(milestone_id)` |
| `payment_accounts` | Stripe/Wise payment methods | `UNIQUE(user_id, provider)` |
| `transactions` | All money movements | `external_transaction_id` unique |
| `reviews` | Post-contract ratings | `UNIQUE(contract_id, reviewer_id)` |
| `conversations` | User-to-user threads | `UNIQUE(participant_one_id, participant_two_id, job_id)` |
| `messages` | Individual messages | Indexed on `conversation_id`, `sender_id` |
| `notifications` | In-app event alerts | Indexed on `user_id`, `type`, `is_read` |

---

## Security

| Feature | Implementation |
|---|---|
| Authentication | Stateless JWT (HS256), 30-min access tokens, 7-day refresh tokens |
| Password storage | bcrypt with salt, minimum complexity enforced at registration |
| Rate limiting | Sliding-window per IP per endpoint tier (swap to Redis for multi-instance) |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy` |
| HSTS + CSP | Enabled automatically when `ENVIRONMENT=production` |
| CORS | Strict origin whitelist |
| Input sanitization | All user-submitted text sanitized before persistence |
| File uploads | MIME type validation + size limits, stored outside web root |
| SQL injection | Prevented by SQLAlchemy parameterized queries |
| Escrow | Funds held until client explicitly approves milestone |
| Access control | Every service method verifies ownership before mutation |

### Rate Limiting Tiers

| Endpoint | Limit | Window |
|---|---|---|
| `/auth/register` | 3 requests | 10 minutes |
| `/auth/login` | 5 requests | 5 minutes |
| Avatar upload | 10 requests | 1 minute |
| Write operations (POST/PUT/DELETE) | 30 requests | 1 minute |
| Read operations (GET) | 120 requests | 1 minute |

---

## Testing

The integration test suite exercises the full API end-to-end, including authentication, the complete contract and milestone lifecycle, payments, messaging, and admin access control.

### Run the tests

```bash
# 1. Truncate all data and reset rate limiter
docker exec kaasb_db sh -c "PGPASSWORD=kaasb_pass psql -h localhost -U kaasb_user -d kaasb_db -c \
  \"TRUNCATE TABLE messages, conversations, reviews, notifications, escrows, transactions, \
    payment_accounts, milestones, contracts, proposals, jobs, users RESTART IDENTITY CASCADE;\""

docker restart kaasb_backend && sleep 8

# 2. Run immediately (rate limiter allows 3 registrations: client + freelancer + admin)
docker exec kaasb_backend sh -c "cd /app && python test_api.py"
```

### Test coverage (26 tests)

| # | Test | Coverage |
|---|---|---|
| 1 | Health Check | `GET /health` |
| 2 | User Registration | Client, freelancer, admin registration + rate limit |
| 3 | Login | JWT token generation for each role |
| 4 | Get Current User | `/auth/me` |
| 5 | Create Job | Client role enforcement |
| 6 | List Jobs | Pagination and filtering |
| 7 | Job Details | Full job data |
| 8 | User Profile | Public profile endpoint |
| 9 | Update Profile | Freelancer profile fields |
| 10 | Submit Proposal | Bid, duplicate rejection (409), role guard (403) |
| 11 | List Proposals | Client/freelancer visibility rules |
| 12 | Respond to Proposal | Shortlist → Accept, job status change |
| 13 | Get Contract | Auto-creation on proposal acceptance |
| 14 | Add Milestones | Amount validation, role enforcement |
| 15 | Milestone Lifecycle | Start → Submit → Revision → Approve → Paid |
| 16 | Payment Accounts | Stripe + Wise setup, duplicate rejection |
| 17 | Fund Escrow | Fee calculation, duplicate prevention |
| 18 | Payment Summary | Balances and transaction history |
| 19 | Rate Limiting | Header presence, limit enforcement |
| 20 | Start Conversation | Self-messaging rejection |
| 21 | Send Messages | Message retrieval, conversation listing |
| 22 | Submit Reviews | Completed contract requirement |
| 23 | Review Stats | Rating aggregation |
| 24 | Notifications | Unread count, mark-read operations |
| 25 | Admin Setup | Admin registration and login |
| 26 | Admin Endpoints | Non-admin rejection (403) on all admin routes |

---

## Production Deployment

### Prerequisites

- A Linux server with Docker and Docker Compose v2
- A domain name pointing to the server
- SSL certificates (or configure Let's Encrypt in `docker/nginx/nginx.conf`)

### 1. Create the production environment file

```bash
cp .env.example .env.production
```

Edit `.env.production`:

```env
# Required
DOMAIN=yourdomain.com
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
DB_USER=kaasb_user
DB_PASSWORD=<strong-random-password>
DB_NAME=kaasb_db

# Payments
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
WISE_API_KEY=...
WISE_PROFILE_ID=...
WISE_ENVIRONMENT=production

# Frontend
NEXT_PUBLIC_API_URL=https://yourdomain.com
```

### 2. Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

The script builds optimized images, starts services in dependency order, runs migrations, and health-checks each container.

### 3. Create the first admin

```bash
./deploy.sh --create-admin
```

### 4. Verify

```bash
curl -sf https://yourdomain.com/health
# Expected: {"status":"healthy","database":"connected"}
```

### Deploy script reference

| Command | Description |
|---|---|
| `./deploy.sh` | Full deployment |
| `./deploy.sh --build` | Build images only |
| `./deploy.sh --migrate` | Run Alembic migrations |
| `./deploy.sh --restart` | Restart all services |
| `./deploy.sh --stop` | Stop all services |
| `./deploy.sh --logs` | Tail service logs |
| `./deploy.sh --status` | Show service health |
| `./deploy.sh --create-admin` | Create a superuser account |

### Production resource limits

| Service | Memory limit |
|---|---|
| Nginx | 128 MB |
| PostgreSQL | 512 MB |
| Redis | 256 MB |
| FastAPI backend | 1 GB |
| Next.js frontend | 512 MB |

---

## Project Structure

```
kaasb/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py        # Auth dependencies (get_current_user, etc.)
│   │   │   └── v1/
│   │   │       ├── router.py          # Route aggregation
│   │   │       └── endpoints/         # 11 route modules
│   │   │           ├── auth.py
│   │   │           ├── users.py
│   │   │           ├── jobs.py
│   │   │           ├── proposals.py
│   │   │           ├── contracts.py
│   │   │           ├── payments.py
│   │   │           ├── reviews.py
│   │   │           ├── messages.py
│   │   │           ├── notifications.py
│   │   │           ├── admin.py
│   │   │           └── health.py
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic settings
│   │   │   ├── database.py            # Async SQLAlchemy engine + session
│   │   │   └── security.py            # JWT token utilities
│   │   ├── middleware/
│   │   │   └── security.py            # Rate limiter + security headers
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── base.py                # BaseModel (id, created_at, updated_at)
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── proposal.py
│   │   │   ├── contract.py            # Contract + Milestone
│   │   │   ├── payment.py             # PaymentAccount + Transaction + Escrow
│   │   │   ├── review.py
│   │   │   ├── notification.py
│   │   │   └── message.py             # Conversation + Message
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── services/                  # Business logic (one service per domain)
│   │   ├── utils/
│   │   │   ├── files.py               # Avatar upload/delete
│   │   │   └── sanitize.py            # Input sanitization
│   │   └── main.py                    # FastAPI app factory + lifespan
│   ├── alembic/                       # Database migrations (4 versions)
│   ├── scripts/
│   │   └── create_admin.py            # CLI: create a superuser
│   ├── test_api.py                    # Integration test suite (26 tests)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js App Router (22 routes)
│   │   │   ├── auth/login/
│   │   │   ├── auth/register/
│   │   │   ├── jobs/
│   │   │   ├── freelancers/
│   │   │   ├── profile/[username]/
│   │   │   ├── dashboard/             # All authenticated pages
│   │   │   └── admin/
│   │   ├── components/
│   │   │   └── layout/navbar.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                 # Axios instance + API helpers
│   │   │   └── auth-store.ts          # Zustand auth store
│   │   └── types/                     # TypeScript type definitions
│   ├── package.json
│   └── Dockerfile
├── docker/
│   ├── backend/Dockerfile             # Python 3.12-slim, multi-stage
│   ├── frontend/Dockerfile            # Node 20-alpine, multi-stage
│   ├── nginx/nginx.conf               # Reverse proxy + SSL termination
│   └── init.sql                       # Database initialization
├── docker-compose.yml                 # Development stack
├── docker-compose.prod.yml            # Production stack (resource limits)
├── deploy.sh                          # Deployment automation
└── README.md
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
