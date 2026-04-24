# Reviews / Ratings Audit

Opened 2026-04-25. User ask: *"check if the notifications and review systems are working correctly and professionally."*

Scope: `reviews` table, `ReviewService`, `/reviews/*` endpoints, rating aggregation on `users.avg_rating` + `services.avg_rating`, and the UI surfaces that read them.

---

## Verdict

**Works for contract-based jobs. Broken for service orders.** Contract reviews are correct and secure; service-order reviews are *impossible to leave today*. That's the main launch blocker. Three secondary gaps follow.

---

## What is already right

- Review uniqueness — one per reviewer per contract ([review.py:32-35](../../backend/app/models/review.py#L32)).
- Rating range — `CHECK rating BETWEEN 1 AND 5` at the DB layer, not just Pydantic.
- Contract-party check — only the two parties can leave a review ([review_service.py:51-56](../../backend/app/services/review_service.py#L51)).
- Completed-contract gate — `ContractStatus.COMPLETED` required.
- Aggregation is atomic and transactional — `_update_user_rating` runs in the same session as the INSERT, so the avg never drifts.
- Service rows get rating mirrored on every review write (2026-04-22 PR-G5).
- Review notifications fire with bilingual copy + link to contract.
- Reviews page `/dashboard/reviews` + profile reviews section hit a cached stats endpoint (`/reviews/user/{id}/stats`).

---

## Findings

### P0 — Launch blocker

**F1. Service orders have no review path.** `ReviewService.submit_review` hard-requires `contract_id`. The gig-style flow (`catalog_service.place_order` → `complete_order`) creates `ServiceOrder` + `Escrow` rows but **never** a `Contract`. After escrow release, there is no surface where the client can rate the freelancer, and no row is ever written. The freelancer's `avg_rating` stays at whatever their last contract review was — often 0 for gig-only sellers.

**Impact**: service listings (`/services`, `/services/[slug]`) show `0 reviews` for sellers who have completed dozens of gig-style orders. This destroys marketplace trust on the exact surface we need to launch. Fiverr-parity gap.

**Fix path**:
1. Add `service_order_id: uuid.UUID | None` column on `reviews`, relax `contract_id` to nullable, add a CHECK constraint that exactly one of the two is set.
2. Widen the `UniqueConstraint` to `(contract_id, service_order_id, reviewer_id)` — still "one review per reviewer per transaction."
3. New endpoint `POST /reviews/order/{service_order_id}` — same validation pattern (must be `COMPLETED`, reviewer must be client-or-freelancer of the order).
4. Auto-nudge notification 24h after `complete_order` if no review written.

Est: 1 migration + ~80 LoC service change + frontend review modal on completed-orders page.

### P1 — Real issues

**F2. No review editability window.** Once submitted, a review is permanent. Fiverr gives a 14-day edit window; Upwork is permanent but allows a public counter-response. Iraqi users are more likely to leave an emotional review and regret it 24h later — no path to fix it.

**Fix**: allow `PATCH /reviews/{id}` from the original reviewer for 24-72h post-submit. Audit-log the edit.

**F3. No reviewee response channel.** If a client leaves a 1-star review claiming the freelancer missed a deadline, the freelancer has zero public recourse — they cannot reply publicly on the review. On Fiverr this is the `seller_response` field shown below the review. Without it, an unjust review is unrecoverable and seller support tickets spike.

**Fix**: add `reviewee_response: Text | null` column, `PATCH /reviews/{id}/response` endpoint, render under the review in the UI.

**F4. `get_reviews_for_user` ignores the reviewer's public profile state.** A reviewer who is deleted / suspended / had their account anonymized can still have their name shown on your public profile. Low risk but worth filtering `Review.reviewer.deleted_at IS NULL`.

### P2 — Polish

**F5. Category ratings (`communication`, `quality`, `professionalism`, `timeliness`) are nullable** — the submit form allows leaving them empty. If only 20% of reviews fill them, the aggregates in `get_review_stats` are misleading. Either make them required on submit (default 5 → user changes), or don't show the averages in the UI unless the sample size ≥ some threshold.

**F6. No moderation queue.** Nothing gates a review for abusive language or personal attacks. Kaasb's F6 chat filter (email / phone / URL / external-app regex) doesn't run on review text. A freelancer could leave "Contact me on WhatsApp +964…" in a review; it goes straight to public profile.

**Fix**: run `MessageFilterService.check_text` on `review.comment` before write; reject with the same pattern as chat sends.

**F7. Review stats don't exclude `is_public=False`** in the mirror path ([review_service.py:139-144](../../backend/app/services/review_service.py#L139)). Current aggregation (`_update_user_rating`) counts ALL reviews — public and private. The public stats endpoint filters correctly (`Review.is_public.is_(True)`), but the freelancer's `avg_rating` stored on `users` includes hidden reviews. Divergence between "what the star bar shows" and "what the list shows." Should filter on both sides.

---

## Not a bug (behaves as designed)

- 1-5 star scale (no half-stars, no 10-point scale) — matches Fiverr / Upwork conventions.
- Contract-based only (historically) — rational when contracts were the only transaction type; F1 is the actual gap.
- `is_public` flag is admin-only — intentionally no user-facing "hide my review."

---

## Recommended sequence

**F1 → F7 → F6 → F3 → F2 → F4 → F5**. F1 unblocks launch. F7 is a 1-line diff. F6 is a cheap trust improvement. F2 + F3 are bigger UX lifts but can be post-launch.
