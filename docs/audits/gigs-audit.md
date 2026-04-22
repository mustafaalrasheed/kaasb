# Gig (Service) Domain Audit — `claude/understand-job-system-v2`

Audit performed 2026-04-22. Branch state: 14 commits on top of main (PR-P1..P4 + PR-N1..N4 + PR-C1..C4 + PR-G0 + 1 lint fix).

Scope: service lifecycle, packages, categories, search+ranking, images, F3 requirements, order placement + payment wiring, order status transitions, F4 structured deliveries, reviews, F5 disputes, F2 seller levels, F6 off-platform filter on order chat, F1 buyer requests, F7 ranking.

## P0 — Ship-blockers

### P0-1 Auto-complete-delivered-orders silently strands orders when freelancer lacks QiCard payout account
**Where:** [backend/app/tasks/marketplace_tasks.py:248](backend/app/tasks/marketplace_tasks.py#L248)
**Symptom:** Orders that have been `DELIVERED` for 3+ days never transition to `COMPLETED` when the freelancer's `payment_accounts.qi_card_phone` or `qi_card_holder_name` is missing.
**Root cause:** `auto_complete_delivered_orders` calls `PaymentService.release_escrow_by_id(...)`. That method validates the freelancer's QiCard payout fields and raises `BadRequestError` when either is missing. The auto-complete loop catches the exception, rolls back the order, logs via `logger.exception`, and silently moves on. The docstring of `release_escrow_by_id` itself (payment_service.py:619) says "Gig-order auto-completion bypasses this check by calling `_release_locked_escrow` directly" — but the actual code doesn't.
**Impact:** Money held hostage: client thinks the platform is holding their escrow (status still `DELIVERED`), freelancer thinks they'll be paid automatically. No admin notification, no metric emitted, no user email. A freelancer who forgets to fill in payout details permanently blocks every one of their orders from auto-completing.
**Fix sketch:** In `auto_complete_delivered_orders`, call `_release_locked_escrow(escrow)` after acquiring `with_for_update()` on the escrow row, matching the docstring. If the freelancer's account is still incomplete at auto-complete time, the release transaction still records (the admin sees it in the pending-payouts tab and handles reconciliation manually once the account is fixed). Add a `SELLER_LEVEL_UPGRADED`-style admin `system_alert` notification when we skip a release for account reasons, so the gap isn't invisible.

### P0-2 Client-side `complete_order` also hits `release_escrow_by_id`, leaving the client with no path to close a legitimate order
**Where:** [backend/app/services/catalog_service.py:746](backend/app/services/catalog_service.py#L746)
**Symptom:** When a client clicks "accept delivery" on a delivered order whose freelancer hasn't set up payout details, they get a 400 error: *"Freelancer's QiCard payout details are incomplete ..."*. The client can't complete their own order; the status stays at `DELIVERED`.
**Root cause:** Same mismatch as P0-1 — the docstring carve-out for gig-order paths isn't actually implemented. The validation that's correct for admin-driven payouts is being applied to client-driven acceptance, where it's the freelancer's account problem, not the client's.
**Impact:** Client receives a confusing error message blaming a counterparty they can't contact directly; they can't leave a review until the order is `COMPLETED`, so reputation feedback is blocked too. Likely support-ticket generator.
**Fix sketch:** Mirror P0-1's fix: have `complete_order` resolve the escrow, acquire `with_for_update()`, and call `_release_locked_escrow` directly. Record the release to the internal ledger regardless; admin manual payout already catches this on their side when they see the pending-payout row.

### P0-3 Stale `PENDING` service orders accumulate indefinitely when payment fails
**Where:** [backend/app/services/catalog_service.py:512](backend/app/services/catalog_service.py#L512), [backend/app/tasks/marketplace_tasks.py:336](backend/app/tasks/marketplace_tasks.py#L336)
**Symptom:** When a client starts checkout but never completes the QiCard redirect (closes the tab, network fails, changes their mind), the `ServiceOrder` row stays at `status=PENDING` forever. Each of these increments `Service.orders_count`, which feeds into `rank_score` — a rage-quit click can permanently boost a service's rank.
**Root cause:** `place_order` increments `orders_count` and creates the row before the QiCard confirm webhook lands. PR-P3 added `flag_stuck_pending_transactions` that counts stuck payment transactions, but there's no equivalent for stuck orders (and the transaction flagger doesn't remediate — only reports to Prometheus).
**Impact:** (a) rank_score inflation (orders that never actually completed or even paid are counted); (b) per-freelancer dashboard clutter ("you have 47 pending orders" that aren't real); (c) inventory UI (`remaining_slots`, if it gets added) drifts from reality.
**Fix sketch:** Add `expire_pending_orders` to `marketplace_tasks.py` — after 30 minutes in `PENDING` with no matching `FUNDED` escrow, transition the order to `CANCELLED` and decrement `Service.orders_count` atomically. Wire it into `run_all`.

## P1 — Should-fix before next release

### P1-1 Disputes cannot be raised on `PENDING_REQUIREMENTS` orders
**Where:** [backend/app/services/catalog_service.py:763-790](backend/app/services/catalog_service.py#L763-L790) (`raise_dispute`)
**Symptom:** A client who pays, realises the questionnaire is a scam, and wants their money back can't — `raise_dispute` only accepts orders in `IN_PROGRESS` / `DELIVERED` / `REVISION_REQUESTED`. `PENDING_REQUIREMENTS` is missing from the allowlist.
**Root cause:** F3 added `PENDING_REQUIREMENTS` to the order state machine but the dispute allowlist wasn't updated.
**Impact:** Client stuck on a freshly-paid order where the freelancer never even started work. The only way out is an admin-issued refund via /admin/disputes — which requires opening a support ticket because the normal "Raise dispute" button rejects.
**Fix sketch:** Add `ServiceOrderStatus.PENDING_REQUIREMENTS` to the acceptable-statuses list in `raise_dispute`. Test to cover the new transition.

### P1-2 24-hour chat suspensions have no admin override UI
**Where:** [backend/app/services/message_filter_service.py](backend/app/services/message_filter_service.py), [backend/app/api/v1/endpoints/admin.py](backend/app/api/v1/endpoints/admin.py) (no `/admin/users/{id}/unsuspend-chat` consumer in frontend)
**Symptom:** When the F6 filter auto-suspends a user for 24h after 3+ off-platform violations, an admin has a backend endpoint to clear the suspension but no frontend control. If the user genuinely had a reason (sharing a client's GitHub URL in an order chat, say), there's no path to unblock except via CLI or direct DB edit.
**Root cause:** `/admin/users/{id}/unsuspend-chat` endpoint exists (confirmed by CLAUDE.md line referencing commit `6cdc706`) but no admin-tab button was wired. Frontend `admin/page.tsx` shows chat-violation count but no action.
**Impact:** False-positive suspensions generate support tickets; admin response time is inflated by the extra server-side step.
**Fix sketch:** Add an "Unsuspend chat" button to the admin users tab that appears when `user.chat_suspended_until > now()`. Call the existing backend endpoint. No schema change.

### P1-3 `users.avg_rating` is updated on review create, but `Service.avg_rating` / `Service.reviews_count` are not
**Where:** [backend/app/services/review_service.py:116-124](backend/app/services/review_service.py#L116), [backend/app/models/service.py](backend/app/models/service.py) (denorm columns on `Service`)
**Symptom:** Posting a review updates the freelancer's `User.avg_rating` immediately. But the per-service rating shown on listing/search pages is either cached stale or computed on every query. If it's denormalised to `Service.avg_rating`/`reviews_count`, those fields aren't recomputed on review creation.
**Root cause:** `review_service.create_review` aggregates reviews per-user, not per-service. No hook into `Service.*` denorm.
**Impact:** Service-level search/sort-by-rating returns stale ordering until the next `marketplace_tasks.refresh_service_rank_scores` nightly run (24h lag on fresh reviews).
**Fix sketch:** Extend `create_review` to look up the service via the completed order's `service_id`, run a UPDATE with an aggregate subquery to refresh `Service.avg_rating` and `reviews_count`. Keep the change `synchronize_session=False` to avoid identity-map churn.

### P1-4 `request_revision` doesn't reset `due_date`
**Where:** [backend/app/services/catalog_service.py:718](backend/app/services/catalog_service.py#L718)
**Symptom:** When a client requests revision on a `DELIVERED` order, the order returns to `REVISION_REQUESTED` status but the original `due_date` stays unchanged — often already in the past. The freelancer's dashboard shows "OVERDUE" immediately on a revision they can't start fixing until the client explains what's wrong.
**Root cause:** `request_revision` only sets status + decrements `revisions_remaining`. No timeline recomputation.
**Impact:** F2 seller-level on-time-delivery metric counts a missed deadline; freelancer's completion signal gets hurt through no fault of their own.
**Fix sketch:** Add `order.due_date = datetime.now(UTC) + timedelta(days=min(order.delivery_days, 3))` — give a cap so a 14-day delivery doesn't silently become another 14 days. Alternatively: introduce a separate `revision_due_date` column so analytics can measure both.

### P1-5 Subcategory `slug` is globally unique, not per-category
**Where:** [backend/app/models/service.py:84](backend/app/models/service.py#L84) (`slug: Mapped[str] = mapped_column(String(120), unique=True, ...)`)
**Symptom:** Two different parent categories can't both have a subcategory with the slug `design` or `logo`. Current seed data avoids the collision, but a future admin adding `/graphic-design/logo` will get a 409 if any other category already has a `logo` subcategory.
**Root cause:** `unique=True` on slug rather than a composite unique on `(category_id, slug)`.
**Impact:** Latent schema constraint that will surface the first time an admin tries to add a duplicate subcategory name under a new parent. Silent today because seed content happened to avoid collisions.
**Fix sketch:** Migration — drop the single-column uniqueness on `service_subcategories.slug`, add `UniqueConstraint("category_id", "slug")`. Data-safe because collisions don't yet exist on the seeded set.

## P2 — Nice-to-have

- **Ranking opacity.** `refresh_service_rank_scores` in [marketplace_tasks.py](backend/app/tasks/marketplace_tasks.py) computes a composite of orders, rating, and freshness; there's no admin-facing breakdown or per-component debug view. Hard to answer "why did my service drop in search?" — add a `GET /admin/services/{id}/rank-breakdown` returning each factor.
- **Image upload limits.** `MAX_SERVICE_IMAGES` is enforced in `add_image` but not in the create flow — if you `create_service` with 10 images in the initial payload, nothing stops it (only the sequential `add_image` calls after). Collapse to one enforcement point.
- **`has_requirements = bool(service.requirement_questions)` in `place_order`.** Line 519 immediately discards the computed value (`_ = has_requirements`). Either use it to set the initial status correctly (overlaps with P0-3 remediation for PENDING cleanup), or delete the dead variable.
- **Order count / impressions race.** `place_order` runs an atomic UPDATE to increment `orders_count`, but impressions is incremented in `get_service_by_slug` without locking. Under heavy concurrent views, SQL `UPDATE ... SET impressions = impressions + 1` is race-free, but it also bypasses the identity map — test coverage would be good.

## Deferred / out-of-scope

- **F1 buyer requests / offers deep review.** Lightweight look: model fine, acceptance flow works. Not auditing further this round.
- **QiCard v1 3DS refund API.** Known Issue #2 in CLAUDE.md — out of code scope; needs merchant provisioning to unblock.
- **Real upload endpoint for chat attachments / MessageAttachment URL convention.** PR-C1 adopted absolute-URL validation but there's still no backend upload endpoint that produces such URLs. Separate initiative.
- **Notification archive admin UI.** PR-N4 added the archive table but there's no admin-visible interface to browse archived notifications. User-visible gap, but a P2 polish concern.
