# Kaasb Launch Decision Log

One row per non-obvious decision taken during the beta → launch work. This exists so future-you (or any admin/engineer who joins later) can answer "why did we choose X?" without archaeology.

Add new rows at the top. Keep each entry short: what was decided, why, who decided, when.

---

## 2026-04-23 — Keep `gig_*` synonym aliases until a dedicated sweep PR

**Decision:** The four legacy SQLAlchemy `synonym("service_*")` aliases (`BuyerRequestOffer.gig_id`, `BuyerRequestOffer.gig`, `Escrow.gig_order_id`, `ServicePackage.gig_id`, `ServiceOrder.gig_id`) stay in place for now.

**Why:** The Phase-1 audit grep showed four non-migration files still depend on the legacy names — [backend/app/services/admin_service.py](../../backend/app/services/admin_service.py), [backend/app/schemas/admin.py](../../backend/app/schemas/admin.py), [backend/app/services/buyer_request_service.py](../../backend/app/services/buyer_request_service.py), [backend/app/schemas/buyer_request.py](../../backend/app/schemas/buyer_request.py). Dropping the synonyms without first updating these call sites would break prod.

**Action:** Defer to a dedicated follow-up PR after Phase 10 (soft public launch). Small cost, not a launch blocker. Tracked as `polish` in the backlog.

---

## 2026-04-23 — Launch plan: solo / no-deadline / lean budget

**Decision:** The end-to-end launch plan assumes a solo build, no hard deadline, and a lean / bootstrap budget.

**Why:** User confirmed scope on 2026-04-23. This drives: (a) sequential phases instead of parallel tracks (except the Legal track, which is mostly waiting on counsel), (b) free / self-hosted tools preferred (Plausible self-hosted over GA4 paid tier; Discord over PagerDuty; Resend free tier), (c) no "we'll hire someone" shortcuts — every step has to be executable by one person.

**Action:** Any deviation from these constraints (adding a teammate, hiring a lawyer on retainer, turning on paid ads) is a material change — log it here and re-check the plan's sequencing.

---

## Template

```
## YYYY-MM-DD — Short title

**Decision:** What you decided in one sentence.

**Why:** The reason. Include the constraint or data that drove it.

**Action:** What flows from this. Where to track it.
```
