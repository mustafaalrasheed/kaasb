# Kaasb Error Budgets

Three weekly-tracked error budgets that gate Phase 10 soft-launch readiness and guide post-launch investment decisions. Reviewed every Monday in the weekly ops review (per [ops-quickstart.md](./ops-quickstart.md)).

Last updated: 2026-04-24. Maintainer: Mustafa Alrasheed.

---

## Why error budgets?

An error budget is the **maximum tolerable failure rate** for a critical user journey. If we're under budget, we have permission to keep shipping features. If we blow through it, we stop feature work until the underlying issue is fixed. This prevents the "we'll fix it eventually" trap where reliability quietly degrades.

These three budgets cover Kaasb's three revenue-critical paths. Other metrics (support SLA compliance, seller-level distribution, category fill-rate) are interesting but not budgeted — those are **observability**, these are **decision-making thresholds**.

---

## Budget 1 — Signup → verified email

**Metric:** `successful_email_verifications / signup_completions` (rolling 7-day window)

**Budget target:** **≥ 95%** (fail budget ≤ 5%)

**Why this number:** users who don't verify email never place an order or accept a proposal. A 5% drop-off is normal; anything higher points to deliverability (Resend reputation, spam filtering) or UX (verification email not clear, link expired too fast) problems.

**How to measure (weekly):**

```sql
SELECT
  COUNT(*) FILTER (WHERE is_email_verified = TRUE) * 1.0
  / NULLIF(COUNT(*), 0) AS verify_rate
FROM users
WHERE created_at >= NOW() - INTERVAL '7 days';
```

**Exits the budget at:** < 95%. Triggers a one-week investigation sprint before any new frontend features ship.

**Current baseline:** N/A until beta opens more widely. Initial target: establish baseline over first 30 days.

---

## Budget 2 — Escrow fund success rate

**Metric:** `successful_escrow_funds / order_placements_with_payment_attempted` (rolling 7-day window)

**Budget target:** **≥ 99%** (fail budget ≤ 1%)

**Why this number:** when a client clicks "Pay Now" and redirects to Qi Card, the result is binary — either funds land in escrow, or the order orphans in PENDING and the client is confused. 1% failure is roughly "Qi Card was briefly unreachable" and acceptable; higher than that is either a Qi Card integration bug on our side or a Qi Card outage that we need to alert around.

**How to measure (weekly):**

```sql
SELECT
  SUM(CASE WHEN e.status IN ('funded', 'released', 'refunded', 'disputed') THEN 1 ELSE 0 END) * 1.0
  / NULLIF(COUNT(*), 0) AS fund_rate
FROM escrows e
JOIN service_orders o ON o.id = e.service_order_id
WHERE o.created_at >= NOW() - INTERVAL '7 days';
```

Or via the Prometheus metric:

```promql
sum(rate(kaasb_escrow_state_transitions_total{new_state="funded"}[7d]))
/
sum(rate(kaasb_business_events_total{event="order_placed"}[7d]))
```

**Exits the budget at:** < 99%. **Stop shipping frontend changes.** Investigate either:
1. `QiCardClient.create_payment` — is it returning non-happy-path responses?
2. `PaymentService.fund_escrow` — is it rejecting valid confirmations?
3. Qi Card status page / their support — is there an upstream issue?

The `HighPaymentFailureRate` Prometheus alert (in [docker/prometheus/alert_rules.yml](../../docker/prometheus/alert_rules.yml)) fires at 5% failure; this budget is stricter and evaluated weekly.

---

## Budget 3 — Dispute rate

**Metric:** `disputes_opened / service_orders_completed_or_disputed` (rolling 30-day window)

**Budget target:** **≤ 2%** (fail budget > 2%)

**Why this number:** disputes are expensive — admin time to review, damage to freelancer reputation even when resolved in their favor, and they indicate upstream mismatch between what clients expected and what sellers delivered. Fiverr and Upwork publish similar numbers around 1.5–3%; 2% is a reasonable mid-point for Kaasb's market.

**How to measure (weekly):**

```sql
SELECT
  SUM(CASE WHEN status = 'disputed' OR dispute_opened_at IS NOT NULL THEN 1 ELSE 0 END) * 1.0
  / NULLIF(COUNT(*) FILTER (
      WHERE status IN ('completed', 'cancelled')
         OR dispute_opened_at IS NOT NULL
    ), 0) AS dispute_rate
FROM service_orders
WHERE created_at >= NOW() - INTERVAL '30 days';
```

**Exits the budget at:** > 2%. Triggers a qualitative review — are specific categories or freelancers driving the rate? Is the auto-complete window (3 days) too short or too long? Are service descriptions accurate?

**Note:** this is the only budget on a **30-day window** rather than 7 — disputes are low-volume and need a larger denominator to be meaningful.

---

## Ancillary watchlist (not budgeted)

These are tracked in the weekly ops review but don't have hard thresholds yet. If one of these shows a 2-week trend, add it as a budget:

| Metric | Watch for |
|--------|-----------|
| First-response support SLA (target: 8h business) | < 90% compliance |
| Payout lag: escrow release → Qi Card transfer confirmed (target: ≤ 4 business days) | > 5 business days |
| New freelancer → first service published | drops below 40% of new signups |
| Service approval turnaround (pending_review → active) | > 48 business hours |
| First signup → first successful order (D7 conversion) | < 10% |

---

## How to run the weekly review

Every Monday, in 30 minutes or less:

1. Open Grafana dashboard "Kaasb Business KPIs" (once shipped; today pull queries from this doc)
2. Note current values of all three budgets
3. If any budget is over — **stop feature work**, log the incident in Discord #launch, start a root-cause doc
4. If all three green — decide what shipped during the week was most impactful and pick the next week's priority
5. Post summary in Discord:

```
Weekly Ops — 2026-XX-XX
- Verify rate: 96.2% ✅
- Escrow fund rate: 99.4% ✅
- Dispute rate (30d): 1.1% ✅
- Biggest shipped: [thing]
- Next week: [priority]
```

---

## Phase 6 lean-scope disclosure

The original launch plan called for **full frontend analytics** (Plausible self-hosted + 6 custom events + analytics script mounted in layout.tsx) in Phase 6. That's deferred to post-launch because:

1. Self-hosted Plausible is a multi-hour deployment (Docker container + its own Postgres + domain routing)
2. Frontend event tracking requires cookie-consent work in an already-consented UX
3. For pre-launch, **server-side business metrics via Prometheus** (which already emit on every critical event per `monitoring.py`) give us 80% of the decision-grade data without the UX tax

**What's still wired:**
- Prometheus `kaasb_business_events_total` counter — fires on order_placed, order_completed, dispute_opened, escrow_funded, etc.
- `kaasb_escrow_state_transitions_total` counter — every escrow state change
- `kaasb_auth_events_total` — signup + verification
- `kaasb_payment_events_total` — Qi Card integration

All three budgets above can be computed from the existing metrics + SQL queries against prod, no frontend work needed.

**When to revisit Phase 6 full scope:** post-launch, once we have >500 weekly active users and need funnel visibility into page-level behavior (bounce rate, time-on-page, drop-off). Before that, guessing at funnel fixes from analytics is premature — we'd iterate on the wrong bottleneck.

---

## Related

- [ops-quickstart.md](./ops-quickstart.md) — where the weekly review is documented as part of the operator routine
- [docker/prometheus/alert_rules.yml](../../docker/prometheus/alert_rules.yml) — the 41 alert rules that cover acute failures; these budgets cover chronic/rolling failures
- [docs/admin/dispute-runbook.md](../admin/dispute-runbook.md) — when dispute rate spikes, the runbook for handling individual cases
- [decision-log.md](./decision-log.md) — crosscutting quality bars (security/SEO/UX/professionalism) that apply alongside these budgets
