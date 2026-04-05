# Kaasb — API Reference

**Base URL:** `https://kaasb.com/api/v1`  
**Auth:** httpOnly cookie (`access_token`). Set automatically on login.  
**Content-Type:** `application/json`

All successful responses:
```json
{ "data": <payload>, "message": "..." }
```

All error responses:
```json
{ "detail": "human-readable error message" }
```

---

## Authentication

### POST /auth/register

Create a new user account.

**Request:**
```json
{
  "first_name": "علي",
  "last_name": "حسن",
  "username": "ali_hassan",
  "email": "ali@example.com",
  "password": "SecurePass123!",
  "primary_role": "freelancer"   // "freelancer" | "client"
}
```

**Response:** `201`
```json
{
  "id": "uuid",
  "email": "ali@example.com",
  "username": "ali_hassan",
  "primary_role": "freelancer",
  "is_email_verified": false
}
```

---

### POST /auth/login

```json
{ "email": "ali@example.com", "password": "SecurePass123!" }
```

**Response:** `200` — Sets `access_token` + `refresh_token` cookies.
```json
{ "message": "تم تسجيل الدخول بنجاح" }
```

---

### POST /auth/refresh

Refresh the access token using the refresh cookie. No body required.

**Response:** `200` — Sets new `access_token` cookie.

---

### POST /auth/logout

Revokes the current refresh token. No body required.

**Response:** `200` — Clears cookies.

---

### POST /auth/logout-all

Revokes all refresh tokens for the current user (increments `token_version`).

**Response:** `200`

---

### GET /auth/me

Returns the currently authenticated user.

**Response:** `200`
```json
{
  "id": "uuid",
  "email": "ali@example.com",
  "username": "ali_hassan",
  "first_name": "علي",
  "last_name": "حسن",
  "primary_role": "freelancer",
  "is_email_verified": true,
  "status": "active",
  "avatar_url": "/uploads/avatars/uuid.jpg",
  "title": "مطور ويب",
  "hourly_rate": 25.0,
  "skills": ["Python", "React"],
  "experience_level": "expert",
  "avg_rating": 4.8,
  "total_reviews": 12,
  "jobs_completed": 8,
  "is_online": true
}
```

---

### POST /auth/social

Social login (Google or Facebook).

```json
{
  "provider": "google",          // "google" | "facebook"
  "token": "<access_token>",     // NOT id_token for Google
  "primary_role": "freelancer"   // Required only for new users
}
```

**Response:** `200` — Sets auth cookies.

---

### POST /auth/phone/send-otp

Send OTP to phone number. Rate-limited: 3 per phone per 10 minutes.

```json
{ "phone": "+9647701234567" }
```

**Response:** `200`
```json
{ "message": "تم إرسال رمز OTP" }
```

---

### POST /auth/phone/verify-otp

```json
{
  "phone": "+9647701234567",
  "otp": "123456"
}
```

**Response:** `200` — Sets auth cookies.

---

### POST /auth/forgot-password

```json
{ "email": "ali@example.com" }
```

**Response:** `200` — Always same response (prevents email enumeration).

---

### POST /auth/reset-password

```json
{
  "token": "<reset-token-from-email>",
  "new_password": "NewSecurePass123!"
}
```

**Response:** `200`

---

### POST /auth/verify-email

```json
{ "token": "<verification-token-from-email>" }
```

**Response:** `200`

---

### POST /auth/ws-ticket

Get a one-time WebSocket authentication ticket (30-second TTL).

**Response:** `200`
```json
{ "ticket": "uuid-ticket" }
```

---

## Jobs

### GET /jobs

List and search jobs.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search (title, description) |
| `category` | string | Filter by category |
| `job_type` | string | `fixed` \| `hourly` |
| `experience_level` | string | `entry` \| `intermediate` \| `expert` |
| `sort_by` | string | `newest` \| `oldest` \| `budget_high` \| `budget_low` |
| `page` | int | Default 1 |
| `page_size` | int | Default 20, max 50 |

**Response:** `200`
```json
{
  "jobs": [ { ...job_summary } ],
  "total": 150,
  "page": 1,
  "total_pages": 8
}
```

---

### POST /jobs

Create a new job. Requires `client` role.

```json
{
  "title": "بناء موقع تجارة إلكترونية",
  "description": "أحتاج موقع متجر إلكتروني ...",
  "category": "برمجة وتقنية",
  "job_type": "fixed",
  "fixed_price": 500.0,
  "experience_level": "expert",
  "duration": "1_to_3_months",
  "skills_required": ["React", "Django", "PostgreSQL"]
}
```

**Response:** `201`

---

### GET /jobs/{id}

Get job details.

**Response:** `200` — Full job object with client info and proposal count.

---

### PUT /jobs/{id}

Update job (owner only, status must be `open`).

---

### DELETE /jobs/{id}

Delete job (owner only, no accepted proposals).

---

### POST /jobs/{id}/close

Close job to new proposals (owner only).

---

## Proposals

### POST /proposals

Submit a proposal. Requires `freelancer` role.

```json
{
  "job_id": "uuid",
  "cover_letter": "أنا مطور متخصص في ...",
  "bid_amount": 450.0,
  "estimated_duration": "6 weeks"
}
```

**Response:** `201`

---

### GET /proposals/my

List all proposals submitted by the current freelancer.

---

### GET /jobs/{job_id}/proposals

List proposals for a specific job (job owner only).

---

### PATCH /proposals/{id}/status

Update proposal status (job owner only).

```json
{
  "status": "accepted",    // "accepted" | "rejected" | "shortlisted"
  "client_note": "..."     // Optional message to freelancer
}
```

---

### DELETE /proposals/{id}

Withdraw proposal (freelancer only, status must be `pending`).

---

## Contracts

### POST /contracts

Create a contract from an accepted proposal (client only).

```json
{
  "proposal_id": "uuid",
  "total_amount": 450.0
}
```

---

### GET /contracts

List contracts for the current user.

**Query:** `status` (active/completed/cancelled/disputed)

---

### GET /contracts/{id}

Get contract details with milestones.

---

### POST /contracts/{id}/milestones

Add a milestone to a contract.

```json
{
  "title": "تصميم الواجهة",
  "amount": 150.0,
  "due_date": "2026-05-01"
}
```

---

### PATCH /contracts/{id}/milestones/{milestone_id}/status

Update milestone status.

```json
{ "status": "submitted" }   // freelancer submits
{ "status": "approved" }    // client approves → triggers payment release
{ "status": "revision_requested", "note": "..." }  // client requests changes
```

---

## Gigs

### GET /gigs

Search gig catalog.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search |
| `category_id` | uuid | Filter by category |
| `subcategory_id` | uuid | Filter by subcategory |
| `min_price` | float | Minimum package price |
| `max_price` | float | Maximum package price |
| `delivery_days` | int | Max delivery days |
| `sort_by` | string | `newest` \| `top_rated` \| `price_low` \| `price_high` |
| `page` | int | Default 1 |
| `page_size` | int | Default 20 |

---

### GET /gigs/categories

List all gig categories with subcategories.

**Response:** `200`
```json
[
  {
    "id": "uuid",
    "name_ar": "برمجة وتقنية",
    "name_en": "Programming & Tech",
    "slug": "programming-tech",
    "icon": "💻",
    "subcategories": [ { "id": "uuid", "name_ar": "...", "slug": "..." } ]
  }
]
```

---

### GET /gigs/{slug}

Get gig detail by slug.

---

### GET /gigs/my

List authenticated freelancer's own gigs.

---

### POST /gigs

Create a new gig (freelancer only).

```json
{
  "title": "سأصمم لك شعاراً احترافياً",
  "description": "...",
  "category_id": "uuid",
  "subcategory_id": "uuid",
  "tags": ["logo", "branding", "design"],
  "packages": [
    {
      "tier": "basic",
      "name": "الباقة الأساسية",
      "description": "شعار بسيط",
      "price": 15000.0,
      "delivery_days": 3,
      "revisions": 2,
      "features": ["PNG", "SVG"]
    },
    {
      "tier": "standard",
      "name": "الباقة المتوسطة",
      "price": 35000.0,
      "delivery_days": 5,
      "revisions": 5,
      "features": ["PNG", "SVG", "ملفات مصدر"]
    }
  ]
}
```

---

### PUT /gigs/{gig_id}

Update a gig (owner only). If gig is `active`, moves to `pending_review`.

---

### DELETE /gigs/{gig_id}

Delete a gig (owner only, no active orders).

---

### POST /gigs/{gig_id}/pause

Pause an active gig.

### POST /gigs/{gig_id}/resume

Resume a paused gig (no re-review needed).

---

### POST /gigs/orders

Place a gig order (client only).

```json
{
  "gig_id": "uuid",
  "package_id": "uuid",
  "requirements": "أريد شعاراً باللون الأزرق مع اسم الشركة..."
}
```

**Response:** `201`
```json
{
  "order_id": "uuid",
  "payment_url": "https://qicard.iq/pay/...",   // Redirect client here
  "amount": 35000.0,
  "currency": "IQD"
}
```

---

### GET /gigs/orders/buying

List gig orders placed by the client.

### GET /gigs/orders/selling

List gig orders received by the freelancer.

---

### POST /gigs/orders/{id}/deliver

Mark order as delivered (freelancer only, status must be `in_progress`).

```json
{ "delivery_note": "تم التسليم، يرجى المراجعة..." }
```

---

### POST /gigs/orders/{id}/revision

Request revision (client only, status must be `delivered`, revisions remaining > 0).

```json
{ "note": "أريد تغيير اللون إلى الأحمر" }
```

---

### POST /gigs/orders/{id}/complete

Mark order as complete (client only, status must be `delivered`). Triggers payment release.

---

## Payments

### GET /payments/summary

Get financial summary for the current user.

**Response (freelancer):**
```json
{
  "total_earned": 250000.0,
  "pending_payout": 50000.0,
  "platform_fees_paid": 25000.0,
  "currency": "IQD"
}
```

**Response (client):**
```json
{
  "total_spent": 175000.0,
  "active_escrow": 35000.0,
  "currency": "IQD"
}
```

---

### GET /payments/transactions

List transaction history.

**Query:** `page`, `page_size`, `type` (payment/payout/refund/fee)

---

### GET /payments/accounts

List connected payment accounts.

### POST /payments/accounts

Add a payment account (e.g., QiCard phone number for payouts).

```json
{
  "provider": "qi_card",
  "qi_card_phone": "+9647701234567"
}
```

---

### POST /payments/escrow/fund

Initiate escrow funding via QiCard.

```json
{
  "contract_id": "uuid",      // For job contracts
  "milestone_id": "uuid",     // Specific milestone
  "amount": 150000.0
}
```

**Response:** `200`
```json
{
  "payment_url": "https://qicard.iq/pay/...",
  "escrow_id": "uuid"
}
```

---

### GET /payments/escrow/{id}

Get escrow status.

---

### POST /payments/payout

Admin only: release payment to freelancer.

```json
{
  "escrow_id": "uuid",
  "note": "Payment released for milestone completion"
}
```

---

## Messages

### GET /messages/conversations

List all conversations for the current user.

**Response:** `200`
```json
{
  "conversations": [
    {
      "id": "uuid",
      "other_user": { "id": "uuid", "username": "...", "avatar_url": "..." },
      "last_message_text": "شكراً لك",
      "last_message_at": "2026-04-05T10:00:00Z",
      "unread_count": 2
    }
  ]
}
```

---

### GET /messages/conversations/{id}/messages

Get messages in a conversation.

**Query:** `before` (cursor UUID for pagination), `limit` (default 50)

---

### POST /messages/conversations/{id}/messages

Send a message.

```json
{ "content": "مرحباً، هل يمكنك إنجاز هذا خلال أسبوع؟" }
```

---

### POST /messages/conversations

Start a new conversation.

```json
{
  "recipient_id": "uuid",
  "job_id": "uuid",          // Optional — link to a job
  "message": "مرحباً..."
}
```

---

### PATCH /messages/conversations/{id}/read

Mark all messages in conversation as read.

### GET /messages/unread-count

```json
{ "unread_count": 5 }
```

---

## Notifications

### GET /notifications

List notifications for the current user.

**Query:** `page`, `page_size`, `unread_only` (bool)

---

### PATCH /notifications/{id}/read

Mark a single notification as read.

### PATCH /notifications/read-all

Mark all notifications as read.

### GET /notifications/unread-count

```json
{ "unread_count": 3 }
```

---

## Users / Profiles

### GET /users/profile/{username}

Get a public user profile.

### PUT /users/profile

Update the current user's profile.

```json
{
  "title": "مطور ويب متخصص",
  "bio": "لدي 5 سنوات خبرة في ...",
  "hourly_rate": 30.0,
  "skills": ["Python", "FastAPI", "React"],
  "experience_level": "expert",
  "portfolio_url": "https://myportfolio.com",
  "country": "العراق",
  "city": "بغداد"
}
```

### GET /users/freelancers

Search freelancers directory.

**Query:** `q`, `skills` (comma-separated), `experience_level`, `sort_by` (`rating`/`rate_low`/`rate_high`/`newest`), `page`

---

## Reviews

### POST /reviews

Submit a review (after contract/order completion).

```json
{
  "contract_id": "uuid",
  "rating": 5,
  "comment": "عمل رائع، التزم بالموعد وجودة عالية",
  "communication_rating": 5,
  "quality_rating": 5,
  "professionalism_rating": 5,
  "timeliness_rating": 4
}
```

---

### GET /reviews/received

Reviews received by the current user.

---

## Reports

### POST /reports

Report content.

```json
{
  "report_type": "job",         // "job" | "user" | "message" | "review"
  "target_id": "uuid",
  "reason": "spam",             // spam | fraud | harassment | inappropriate_content | fake_account | other
  "description": "هذه الوظيفة وهمية..."
}
```

---

## Admin Endpoints

All require `admin` role.

### GET /admin/stats

Platform statistics.

```json
{
  "total_users": 1250,
  "total_freelancers": 800,
  "total_clients": 450,
  "active_gigs": 320,
  "total_orders": 2100,
  "revenue_iqd": 52500000.0,
  "pending_payouts": 8,
  "pending_gig_reviews": 5
}
```

---

### GET /admin/users

List all users with filters.

**Query:** `q` (search), `role`, `status`, `page`

### PUT /admin/users/{id}/status

Update user status.

```json
{ "status": "suspended", "reason": "Policy violation" }
```

---

### GET /admin/jobs

List all jobs.

### PUT /admin/jobs/{id}/status

```json
{ "status": "closed" }
```

---

### GET /admin/gigs/pending

List gigs awaiting moderation.

### POST /admin/gigs/{id}/approve

Approve a gig for publication.

### POST /admin/gigs/{id}/reject

```json
{ "reason": "الصور غير واضحة، يرجى رفع صور أعلى جودة" }
```

---

### GET /admin/transactions

List all transactions.

**Query:** `type`, `status`, `page`

---

## WebSocket

### Connect

```
wss://kaasb.com/api/v1/ws/{ticket}
```

1. Get ticket: `POST /auth/ws-ticket`
2. Connect with ticket in URL
3. Ticket expires after 30 seconds (connection persists after that)

### Events received (server → client)

```json
// New message
{ "type": "new_message", "conversation_id": "uuid", "message": { ...message } }

// New notification
{ "type": "notification", "notification": { ...notification } }

// Order status change
{ "type": "order_status", "order_id": "uuid", "status": "delivered" }

// Presence
{ "type": "user_online", "user_id": "uuid" }
{ "type": "user_offline", "user_id": "uuid" }
```

### Ping/pong

Send `{"type": "ping"}` every 30 seconds to keep connection alive. Server replies `{"type": "pong"}`.

---

## Health

### GET /health

Basic health check (public).

```json
{ "status": "ok" }
```

### GET /health/detailed

Detailed health (requires `Authorization: Bearer <HEALTH_BEARER_TOKEN>`).

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "disk_free_gb": 45.2,
  "version": "2.0.0"
}
```

---

## GDPR

### POST /gdpr/export

Request a data export. Returns download link via email within 24 hours.

### DELETE /gdpr/account

Permanently delete account and anonymize data.

```json
{ "password": "current_password", "confirm": "DELETE MY ACCOUNT" }
```

---

## Error Codes

| HTTP | Code | Meaning |
|------|------|---------|
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or expired token |
| 403 | Forbidden | Authenticated but not authorized (wrong role) |
| 404 | Not Found | Resource doesn't exist or soft-deleted |
| 409 | Conflict | Duplicate (e.g., email already registered, already submitted proposal) |
| 422 | Unprocessable | Validation error (field-level errors in `detail`) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Bug — check Sentry |

See [docs/api/error_codes.md](api/error_codes.md) for field-level validation error format.
