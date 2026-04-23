# Fiverr Parity Notes

User-contributed research (2026-04-23) mapping Fiverr's buyer + seller + buyer-request flows onto Kaasb's current implementation. Source: three YouTube tutorials (2025 Seller Account Guide, First Order Like a Pro, Buyer Request Tutorial) transcribed + structured by the user.

Use this as a **UX reference** when doing Phase 7 content + polish work. Don't treat as a to-do list — Kaasb already implements most of the core mechanics; this is a gap-finder.

---

## Coverage matrix — where does Kaasb already match?

| Fiverr mechanic | Kaasb status | Evidence |
|-----------------|--------------|----------|
| Single account handles buy + sell | ✅ | `User.primary_role` flips; one row per person |
| 3-tier service packages (Basic/Standard/Premium) | ✅ | `ServicePackage` + `ServicePackageTier` enum |
| Extras (revisions, fast delivery, etc.) | ✅ | `ServicePackage.revisions`, `delivery_days` |
| Requirements questionnaire at order start | ✅ | F3 — `service.requirement_questions` JSONB + `service_orders.requirement_answers` |
| Escrow → work → release flow | ✅ | `Escrow` model, `fund_escrow` / `release_escrow` |
| 3-day auto-complete after delivery | ✅ | F4 — `auto_complete_delivered_orders` cron in marketplace_tasks.py |
| Seller levels (Top Rated / Level 2 / Level 1 / New) | ✅ | F2 — `sellerlevel` enum + daily recalc |
| Buyer request + seller offers | ✅ | F1 — `buyer_requests` + `buyer_request_offers` tables |
| Anti off-platform contact filter | ✅ | F6 — `MessageFilterService` + `violation_logs` |
| Dispute flow with refund/release | ✅ | F5 — `Dispute` model, admin resolves via `/admin/disputes` |
| Gig image gallery | ✅ | shipped 2026-04-18 — `services.images` ARRAY |
| Message thread per order | ✅ | `ConversationType.ORDER` + `order_id` on conversation |
| System messages on dispute open/resolve | ✅ | message_service events |
| Review system (1–5 stars, per contract) | ✅ | `Review` model with UNIQUE constraint |
| Order expiration (stale PENDING auto-cancel) | ✅ | F7 — `expire_stale_pending_orders` task |
| Seller rating mirrored onto services | ✅ | PR-G5 (2026-04-22) — `_update_user_rating` updates Service.avg_rating |

---

## Why we keep Jobs/Proposals alongside Services/Gigs

Fiverr only has Gigs + Buyer Requests. Kaasb has a third model — **Jobs + Proposals** — which Upwork uses. These three coexist deliberately:

| Model | Who starts | Best for |
|-------|-----------|----------|
| **Services (Gigs)** | Freelancer posts a productized offering | Well-defined work — logo, voiceover, proofreading |
| **Jobs** | Client posts what they need done | Custom scope — "Build my website," "Run my podcast edits" |
| **Buyer Requests** | Client posts a short brief, sellers offer | Fast quote on small work, bridge between the two |

Iraqi market is small enough that forcing a user to choose "am I a Fiverr user or an Upwork user?" would be a bad UX. All three stay. Don't collapse Jobs into Services just because Fiverr only has one.

---

## Gaps worth closing for Phase 10 (soft launch)

These are the user-visible gaps — worth a small sprint during Phase 7.

### 1. "Switch to Selling" navbar toggle

Fiverr has an explicit mode toggle ("Switch to Selling") at the top of the nav for users who have both roles. Kaasb shows the same user different dashboards (`/dashboard` for client-facing stats vs freelancer-facing stats) but has no explicit mode toggle.

**Why it matters:** users who act as both buyer AND seller get confused about where to find their freelance orders vs. their client orders. A toggle makes the mental model explicit.

**Effort:** Small frontend change. Add a toggle in the navbar that flips a cookie `kaasb_active_role` (CLIENT / FREELANCER) and rerenders the dashboard accordingly.

### 2. Rich seller onboarding (multi-step)

Fiverr's onboarding walks a new seller through:
1. Primary goal ("sell freelance services")
2. Freelancer type (side hustle / solo / agency)
3. Experience level
4. Profile (name, photo, 600-char bio, languages, skills, education)
5. Security (email + phone verification)
6. Research existing gigs
7. Create first gig

Kaasb's current flow: register → basic profile form → dashboard. No guided "first gig" walkthrough.

**Why it matters:** freelancers who don't publish a gig within their first session churn. Guided onboarding materially moves conversion.

**Effort:** Medium. Multi-step wizard component + progress bar on `/dashboard/onboarding`. Could be 3-5 days of frontend work. Worth it.

### 3. Custom offers sendable from any order chat — highest-leverage gap

Fiverr's seller can send a "Custom Offer" inside ANY chat (not just responding to buyer requests). This lets a seller quote a specific price for a specific scope as a message-level attachment.

Kaasb currently: custom pricing only via Buyer Requests. If a client contacts a freelancer directly via the services page, they have to purchase a pre-defined package at the published price — no negotiation.

**Why it matters:** captures the price-negotiation flow that happens on every marketplace. Without it, returning clients who know which freelancer they want to work with have no way to quote a custom scope without going through the Buyer Request flow (heavier, slower, broadcast to others).

**User question on 2026-04-23:** "Can we use this instead of our Jobs/Proposals model?" — No. Jobs and Custom Offers serve different buyer intents (broadcast-and-bid vs. bilateral-quote). Keep both. Custom Offers add a third entry-point into the order-creation flow; they do not replace Jobs.

**Proposed UX:**
1. Inside any chat, seller sees a "Send Custom Offer" button
2. Modal: title, description, price (IQD), delivery days, revisions
3. Posts as a chat attachment — message card with Accept/Reject/Counter buttons
4. Accept → QiCard checkout for that amount → funds escrow → creates a ServiceOrder
5. Reject/Counter → conversation continues

**Backend effort:** ~2 days. `buyer_request_offers` already has most of the data model; add a `direct_offer` variant that doesn't require an open BuyerRequest. One endpoint to convert an accepted offer into a ServiceOrder.

**Frontend effort:** ~1-2 days. New modal, new message-attachment type.

**Priority:** Phase 7 (content polish). Order after the Switch-to-Selling toggle + seller onboarding wizard since those unblock broader UX first.

---

## Gaps to defer past Phase 10

These are Fiverr features worth knowing about but not launch-blocking:

- **Live Portfolio** — seller publishes completed work as a public sample, client approves. Post-launch Phase 13+.
- **Brief Matching** — Fiverr's AI-driven matching of buyer requests to sellers. Post-launch; requires significant algo work.
- **Bid quota** (Fiverr: 10 bids per seller per day) — anti-spam mechanic. Worth adding once we see actual spam, not preemptively.
- **Fast delivery extras** (pay +$X for 1-day vs 3-day) — can be layered onto `ServicePackage.delivery_days` later; not a launch blocker.
- **Public profile URL as brand (fiverr.com/username)** — Kaasb has `/profile/[username]` already. This is a UX polish: Fiverr lets sellers share `fiverr.com/username` as their "work page." Kaasb could add `kaasb.com/@username` as a shorter vanity URL. Phase 11+ SEO-content work.
- **Fiverr's "get paid in 2 weeks after completion"** — they hold longer for non-Top-Rated sellers. Kaasb currently releases to admin payout queue immediately, then admin transfers manually. Different model; Iraqi market prefers faster payouts; keep Kaasb's approach.

---

## Fiverr mechanics Kaasb should explicitly NOT copy

- **USD-first pricing** — Kaasb is IQD-native per Known Issue #5 resolution. Don't show USD anywhere.
- **Global ID verification** — Fiverr does intense identity checks. For Iraqi market, QiCard itself provides identity binding (cardholder name); we don't need Fiverr-level KYC.
- **Fiverr's 20% take rate** — Kaasb is at 10% (`PLATFORM_FEE_PERCENT`). Keep it lower; Iraqi market can't bear 20%.
- **Disabling off-platform contact by pattern-masking words** — Kaasb's F6 anti-circumvention filter is less heavy-handed; a softer UX wins trust with Iraqi small businesses who legitimately need to exchange phone numbers for in-person delivery.

---

## Buyer workflow mapping

Fiverr's buyer journey as described in the research, with Kaasb equivalent:

| Fiverr step | Kaasb equivalent | Status |
|-------------|------------------|--------|
| Join (email/Google/FB) | `/auth/register` + social login | ✅ |
| Search + filter services by language | `/services` catalog with filters | ✅ (language filter present) |
| Browse price / reviews / seller level | Service cards show price, rating, seller level | ✅ (F2 seller levels) |
| Select gig → review demos + reviews | `/services/[slug]` detail page | ✅ |
| Select package (Basic/Standard/Premium) | Package tier selector | ✅ |
| Customize order (word count, extras) | Extras partially wired; custom quantities are via buyer_request | ⚠️ |
| Checkout → pay subtotal + service fee | Qi Card redirect → payment/result | ✅ |
| Provide requirements | F3 requirements submission modal | ✅ (shipped 2026-04-20) |
| Receive delivery → revisions/accept/dispute | Order detail page actions | ✅ (F4 + F5) |

**Fiverr-specific UX we might adopt:**
- Itemized checkout summary ("Subtotal $220, service fee $13.20, total $233.20") — right now Kaasb shows IQD totals but doesn't always break out the 10% platform fee vs base price prominently on checkout
- Post-checkout timer countdown visible on order page — Kaasb has delivery deadline but should surface "X days Y hours remaining"

---

## Seller workflow mapping

| Fiverr step | Kaasb equivalent | Status |
|-------------|------------------|--------|
| Switch to Selling mode | Not present — separate dashboards | ❌ gap #1 above |
| Create New Gig wizard | `/dashboard/services/new` | ✅ partial (shipped 2026-04-18, could be richer) |
| Gig Title + Category + Metadata tags | Present | ✅ |
| Pricing packages (Basic/Standard/Premium) | Present | ✅ |
| Extras | Partially present — package `revisions` + `delivery_days` | ⚠️ |
| Description + FAQ | Description present, FAQ per-gig is **missing** | ⚠️ |
| Requirements questionnaire | F3 | ✅ |
| Gallery upload (3+ images/video) | Shipped 2026-04-18 | ✅ |
| Submit for admin review | `pending_review` → `active` via admin tab | ✅ |

**Gaps worth closing in Phase 7:**
- Per-gig FAQ field (Fiverr sellers can add FAQs that render on the service page)
- Extras checkout flow (add-ons at purchase time, not just package selection)

---

## Buyer Request workflow mapping

| Fiverr step | Kaasb equivalent | Status |
|-------------|------------------|--------|
| Buyer posts a request with description + files + category + delivery + budget | `/dashboard/requests` → POST `/buyer-requests` | ✅ F1 |
| Fiverr reviews → approves → posted | Kaasb currently auto-approves on post | ⚠️ (may want admin pre-approval to match Fiverr) |
| Buyer manages requests (active/pending/unapproved) | `/dashboard/requests` client view | ✅ |
| Sellers see buyer requests filtered by their skills | `/requests` browse page | ✅ |
| Sellers send personalized offer with portfolio sample | Offer message + price + optional gig link | ✅ |
| Daily bid limit (Fiverr: 10 bids/day) | **Missing** | ❌ |
| Buyer reviews offers → accepts/edits/refuses | Review offers UI | ✅ |

**Worth adding to Phase 11:** daily bid quota to prevent spam as we scale.

---

## Takeaway for the plan

This Fiverr research validates that Kaasb's core mechanics are already correct. The marketplace architecture is sound. Launch is not blocked by missing features — it's blocked by:

1. Payment gateway work (Phase 4, deferred to end)
2. Test coverage (Phase 5)
3. Content gaps — some of which this doc identifies as Phase 7 items (switch-to-selling toggle, richer seller onboarding, per-gig FAQs, custom offers)
4. Legal review (parallel track)
5. Real supply + demand seed content (Phase 7)

Use this doc during Phase 7 planning as the scope boundary: close gaps #1 + #2 + maybe #3 from above, defer everything else.
