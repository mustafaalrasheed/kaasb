# Support + Dispute Systems Audit

Opened 2026-04-25. User ask: *"check and verify that the support, and dispute are working correctly."*

Scope: SUPPORT conversation flow (contact form → admin triage), dispute lifecycle (raise → freeze → resolve), admin tools, user-facing surfaces.

---

## Verdict

- **Support system — works with one confusion gap.** Two overlapping entry points (`POST /messages/support` for users, `POST /admin/support/conversations/*` for staff) both work but sit in different routers; nothing is broken, but the split is a maintenance foot-gun. Access control, claim/release, and user-reply-reopens-to-OPEN semantics are all correct.
- **Dispute system — works correctly at the service layer, broken on the front end.** The API is right (escrow freezes, states transition correctly, admin UI resolves to release or refund, both parties + all staff notified). **The client cannot open a dispute from the UI.** The `raiseDispute` API client exists in `services.ts`, the `POST /services/orders/{id}/dispute` endpoint exists, but no button in `/dashboard/services/orders` calls either. **Shipped this session** — see below.

---

## What is already right

### Support
- `ConversationType.SUPPORT` is scoped to staff-only read/write ([message_service.py:178](../../backend/app/services/message_service.py#L178), [:320](../../backend/app/services/message_service.py#L320)).
- `list_support_conversations` returns only tickets assigned to the calling staff **or** unassigned ([message_service.py:699](../../backend/app/services/message_service.py#L699)) — no staff can see another's claimed ticket.
- Claim is idempotent for the same staff; release is assignee-only; resolve marks `resolved_at`; user replying to a RESOLVED ticket re-opens it to OPEN ([message_service.py:455](../../backend/app/services/message_service.py#L455)).
- `contact_support()` resolves the first active superuser admin at call time, so users don't need to know admin UUIDs. Returns a clean 400 "Support is temporarily unavailable" if there are no active admins (fail-safe) ([messages.py:512](../../backend/app/api/v1/endpoints/messages.py#L512)).
- `/help` page already published with SLA commitment ("reply within 8 business hours, resolve within 48"), bilingual ([help/page.tsx](../../frontend/src/app/help/page.tsx)).
- `is_support` role separation is clean: support staff can triage, claim, release, resolve, and read any SUPPORT + ORDER thread; financial actions (escrow release, user-status change, admin promote) stay `is_superuser`-gated ([dependencies.py:79-93](../../backend/app/api/dependencies.py#L79)).

### Dispute
- Unique constraint on `disputes.order_id` prevents duplicate rows per order ([dispute.py:48](../../backend/app/models/dispute.py#L48)).
- Opening a dispute atomically transitions the escrow from `FUNDED` → `DISPUTED` in the same transaction as the order flip to `DISPUTED`. `release_escrow_by_id` blocks on non-`FUNDED` status, so no race window lets a payout slip through mid-dispute ([catalog_service.py:835](../../backend/app/services/catalog_service.py#L835), [payment_service.py:629](../../backend/app/services/payment_service.py#L629)).
- Allowed open-dispute statuses are `PENDING_REQUIREMENTS`, `IN_PROGRESS`, `DELIVERED`, `REVISION_REQUESTED` ([catalog_service.py:808](../../backend/app/services/catalog_service.py#L808)) — `PENDING_REQUIREMENTS` is deliberately included so a client with a fraudulent freelancer has an exit before they've submitted their brief.
- System messages in the ORDER conversation on open + resolve — both parties see a "Dispute opened — escrow frozen" / "Dispute resolved — outcome: X" trail in their order chat ([catalog_service.py:845](../../backend/app/services/catalog_service.py#L845), [:952](../../backend/app/services/catalog_service.py#L952)).
- Notifications fire: the other party + all staff on open, both parties + the resolving admin on resolve ([dispute_service.py:106](../../backend/app/services/dispute_service.py#L106)).
- Admin UI surfaces disputed orders, shows the order conversation for context, and resolves with release-or-refund + admin note ([admin/tabs/disputes-tab.tsx](../../frontend/src/app/admin/tabs/disputes-tab.tsx)).

---

## Findings

### P0 — Shipped this session

**F1. Client couldn't open a dispute from the UI.** Backend had everything — endpoint, service, escrow-freeze, notifications, system messages. Frontend had `servicesApi.raiseDispute` wired. But `/dashboard/services/orders/page.tsx` rendered a `disputed` status badge without ever providing a way to reach that state. The only path was via support, which turns into an admin doing it manually.

**Fix (shipped)**: red "Report a Problem" button on the buyer-side order card when status ∈ `{pending_requirements, in_progress, delivered, revision_requested}`. New `DisputeModal` requires ≥ 20-char reason, warns that escrow freezes, bilingual, RTL-safe.

### P1 — Real gaps

**F2. Freelancer cannot escalate a client problem.** The `raise_dispute` service enforces `only the client can raise a dispute` ([catalog_service.py:800](../../backend/app/services/catalog_service.py#L800)). A freelancer with a client who refuses to accept delivery, ghosts after requirements, or abuses the revision mechanism has no symmetric path — their only recourse is contacting support, which then manually opens the dispute. This is a quiet asymmetry that favors the client and can be weaponized.

**Fix path**: allow freelancers to raise disputes too, but filter to stricter statuses (probably only `DELIVERED` or `REVISION_REQUESTED` — i.e. work has already happened). Pre-delivery disputes from freelancers are rarely legitimate.

**F3. No evidence-attachment UI for disputes.** The `disputes` model has `evidence_files: list[str]` but the FE reason form is a single textarea — users cannot attach screenshots, delivered files, chat exports, or the client's message history. Admin resolution becomes he-said-she-said without these.

**Fix**: wire the existing chat-attachment uploader onto the dispute modal. Save URLs to `dispute.evidence_files`.

**F4. Two overlapping support entry points — `/messages/support` vs. `/admin/support/conversations/*`.** Both work. They sit in different routers, route to different service methods, and have subtly different semantics. Future-you will not remember which is which. Not a bug; a maintenance liability.

**Fix**: unify under `/messages/support` for user writes + `/support/*` router for staff operations. Deprecate `/admin/support/conversations/*` over one release.

### P2 — Polish

**F5. SLA text is on `/help` but not on the Contact Support modal.** The user sees "we'll respond in 8h" only if they happen to visit `/help` first. A one-line copy addition to the contact modal would set expectations right at the commit point.

**F6. No "close ticket" action for the user.** If an issue resolves itself, the user can't mark the ticket resolved — only staff can. Minor.

---

## Not a bug (behaves as designed)

- **Release-escrow sets status back to `FUNDED` before calling `_release_locked_escrow`** ([catalog_service.py:922](../../backend/app/services/catalog_service.py#L922)). The rehydration from `DISPUTED` → `FUNDED` → released is intentional; the `SELECT FOR UPDATE` inside the release path prevents races.
- **Support staff viewing a SUPPORT thread doesn't clear the user's unread flag.** Correct: the original participant needs to see when the admin actually read their message.
- **Dispute can be opened on `PENDING_REQUIREMENTS` orders.** Deliberate — covers the fraud case where a freelancer disappears before the client's brief is submitted.
- **Only client can open a dispute (not freelancer)** — designed, but listed as F2 because it's worth revisiting before launch.

---

## Recommended sequence

**Shipped**: F1 (dispute UI button).

Next pass: **F3 (evidence upload)** → **F2 (freelancer-initiated disputes)** → **F4 (unify support endpoints)** → **F5 + F6**. F3 is the highest-value for admin triage quality. F2 is a small service-layer change. F4 is a cleanup that will keep paying dividends as the codebase grows.
