# Dispute Resolution Runbook

How a Kaasb admin resolves a service-order dispute end-to-end. Use this when you get a notification that a dispute was opened, or when Rasheed / `admin@kaasb.com` hand you one.

Last updated: 2026-04-23. Maintainer: Mustafa Alrasheed.

---

## Scope

This runbook covers disputes on **service orders** (gigs). Job/proposal/contract disputes follow the separate [contract-dispute-runbook](./contract-dispute-runbook.md) — not yet written.

**Do NOT** use this runbook to:
- Unfreeze an escrow that isn't disputed (use `/admin/escrows/{id}/release` via the normal payouts flow — see [payout-runbook.md](./payout-runbook.md))
- Refund a completed order (that's a refund case, see [refund-runbook.md](./refund-runbook.md))
- Respond to a support ticket that hasn't escalated to a dispute yet (see [support-runbook.md](./support-runbook.md))

---

## Prerequisites

Before you start:

- You are an admin (`is_superuser=True`) on kaasb.com
- You can log into `https://kaasb.com/admin`
- The dispute is in `OPEN` or `UNDER_REVIEW` state (not already resolved or cancelled)
- You are **not** a party to this order — per `admin_service.resolve_dispute`, an admin can resolve any dispute, but if you're personally connected to either party (friend/family of client or freelancer), recuse and ask another admin.

---

## Data model (for reference — what you'll see in the UI)

| Field | Meaning |
|-------|---------|
| `initiated_by` | "client" or "freelancer" — who opened the dispute |
| `reason` | One of: `quality`, `deadline`, `communication`, `not_as_described`, `other` |
| `description` | Free-text reason supplied by the initiator |
| `evidence_files` | Array of uploaded file URLs (screenshots, docs, etc.) |
| `status` | `open` → `under_review` → `resolved_refund` OR `resolved_release` OR `cancelled` |
| `admin_id` | Which admin took the case |
| `admin_notes` | Your notes, visible to other admins (not to client/freelancer) |
| `resolution` | `release` or `refund` (finalized outcome) |

Resolution outcomes are **binary** — no partial splits. If a case genuinely calls for 50/50, resolve with `refund` and then initiate a separate manual transfer for the freelancer's share via the QiCard portal (log it in admin_notes).

---

## Step 1: Intake — find and claim the dispute

1. Log into https://kaasb.com/admin → **Disputes** tab
2. Filter by status = `open` — these are brand-new, unclaimed
3. Click a row to see the full dispute
4. Click **"Take this case"** (or manually set yourself as `admin_id` via the backend if the UI is unresponsive) — this moves status to `under_review` and prevents other admins from touching it

If another admin is already listed as `admin_id` and they're not actively working it (check the conversation timestamps in the order chat), message them before claiming — no duplicated effort.

## Step 2: Gather evidence

You have **four** sources of ground truth for every dispute:

1. **The order itself** — service description, package details, delivery deadline, price, any requirement answers the client submitted (F3 requirements). Click the order link from the dispute view.
2. **The order conversation** — the chat between client and freelancer. Look for explicit scope changes, delays, or promises. The full message thread is accessible via the admin's order-chat view (Disputes tab → "View order chat").
3. **Delivery artifacts** — the `/gigs/orders/{id}/deliveries` list shows every delivery + revision the freelancer submitted, with messages and file URLs. Open each one.
4. **Dispute evidence files** — uploaded by the initiator when opening the dispute.

Cross-reference what was **promised** (service description + package tier + conversation) with what was **delivered** (delivery artifacts + chat acknowledgments). The gap, if any, is the dispute.

## Step 3: Decision tree

Ask these questions in order. The first "yes" tells you the outcome.

### Refund to client (`resolution="refund"`)

- Did the freelancer **not deliver anything** (zero deliveries, order past deadline)? → **refund**
- Did the freelancer deliver something obviously off-scope — e.g., ordered a 5-page article, got a Canva template? → **refund**
- Is the evidence clear-cut that the delivery is **fraudulent or plagiarized** (watermarks from stock sites, verifiable copy-paste, wrong language)? → **refund**
- Did the freelancer **ghost** the client for >72h during the active order (no messages, no status updates, despite client attempts)? → **refund**

### Release to freelancer (`resolution="release"`)

- Did the freelancer deliver on time, on scope, and the client's dispute is about **subjective quality** ("I don't like the colors") that wasn't specified in requirements? → **release**
- Did the client's dispute arrive **after the 3-day auto-complete window** and they're reaching back for a refund retroactively? → **release** (auto-complete means implicit acceptance)
- Did the client change scope mid-order and the freelancer followed the **original** scope? → **release**
- Are you 70%+ confident the freelancer did what was asked? → **release**. (We favor the freelancer when evidence is ambiguous — protects the supply side of the marketplace.)

### When you're genuinely stuck

Ask the other admin for a second opinion in the admin Discord / WhatsApp group (not in public). If still stuck after two admins, **default to refund**. A client who got their money back will try again; a freelancer who got released an order they didn't deserve damages platform trust irrecoverably.

## Step 4: Execute

### Release to freelancer

1. In the dispute view, click **"Resolve: Release"**
2. Fill in `admin_notes` — what you checked and why you decided. One paragraph is enough. This is permanent, the freelancer does NOT see it, other admins DO.
3. Fill in `resolution_message_to_parties` (if the UI has one) — what both parties see. Neutral and brief: "After review, the delivery matched the order scope. Escrow released."
4. Click **Confirm**

Behind the scenes:
- Dispute status → `RESOLVED_RELEASE`
- Order status → `COMPLETED`
- Escrow released → funds become "available for payout" in the freelancer's balance (the actual QiCard transfer still requires a manual admin payout per [payout-runbook.md](./payout-runbook.md))
- System message added to order chat saying "Dispute resolved — escrow released to freelancer"
- Notifications sent to both parties

### Refund to client

1. In the dispute view, click **"Resolve: Refund"**
2. Same `admin_notes` + `resolution_message_to_parties` fields
3. Click **Confirm**

Behind the scenes:
- Dispute status → `RESOLVED_REFUND`
- Order status → `CANCELLED`
- Escrow refunded → this currently falls back to **manual QiCard refund** per Known Issue #2 (programmatic refund via v1 3DS API is Phase 4 work)
- System message in order chat
- Notifications sent to both parties

**Because refunds are manual until Phase 4 ships:** after clicking Resolve:Refund in Kaasb, follow the [refund-runbook.md](./refund-runbook.md) to actually move the IQD back to the client via the QiCard merchant portal, then record the transaction ID in the dispute's `admin_notes` via a separate admin edit.

## Step 5: Post-resolution

Within 24 hours:

1. **Check Sentry** — if the resolution triggered any backend exception, it'll show up there
2. **Check the user conversation** — client/freelancer may reply to the system message. If they're angry or want to appeal, send them to `support@kaasb.com` (don't start DMing privately)
3. **Log the outcome** in the admin Discord #disputes channel (one line: dispute ID, outcome, reason)

---

## Common scenarios & typical outcomes

### Scenario A: "Freelancer disappeared after taking the order"

- Client reports no response in chat for 4+ days
- No deliveries submitted
- Order is past the delivery deadline

**Outcome:** refund. Note `chat_violations` on freelancer if the ghost pattern repeats.

### Scenario B: "This isn't what I ordered"

- Delivery submitted and on time
- Client claims the delivery doesn't match what was promised

Check: service description + package tier + pre-order chat + F3 requirement answers. If the delivery matches all four: **release**. If any material mismatch: **refund**.

### Scenario C: "The quality is bad"

- Delivery on time, on scope, but the client is unhappy with the result
- No objectively measurable failure (no missing features, no broken files)

**Outcome:** release — subjective quality is not disputable once scope is met. Tell the client in the resolution message they can book revisions or leave a review; escrow is released.

### Scenario D: "Freelancer asked for more money mid-order"

- Client provides chat screenshots showing the freelancer demanding extra payment
- Off-platform payment pressure is against TOS

**Outcome:** refund + flag the freelancer's account for admin review. One strike → warning. Two strikes → suspension. Three strikes → ban.

### Scenario E: "I paid but the freelancer never got the order"

- Payment confirmed, but order stuck in `PENDING` (F7 expired stale-orders cron may have cancelled it)
- Escrow likely refunded automatically

**Outcome:** this probably isn't a real dispute — the order auto-cancelled. Check `Escrow.status` — if `refunded`, the dispute is misfiled, cancel it with a note.

### Scenario F: "Both sides claim they're right"

- Evidence is genuinely ambiguous (e.g., client said "fast delivery," freelancer met contract deadline but client wanted faster)
- Both parties acting in good faith

**Outcome:** review in the admin group. If still tied, default to refund (see Step 3 last line).

---

## Edge cases

- **Order has multiple deliveries and only the first was bad** — count the accepted final delivery, not the first attempt. Release if the latest delivery is acceptable.
- **Dispute opened after auto-complete** — order status is `COMPLETED` already, escrow released. You can't use this runbook. The client must go through `refund-runbook.md` which requires admin override and a manual QiCard reverse transfer.
- **Freelancer has >3 disputes in 30 days** — regardless of this specific outcome, flag the account in admin chat and consider a temporary suspension.
- **Dispute amount >500,000 IQD** — per decision-log `PAYOUT_APPROVAL_THRESHOLD_IQD`, large release resolutions fall under dual-control (needs second admin to confirm the payout after the dispute resolves to `release`).

---

## Don't do list

- ❌ Don't DM a party directly about their dispute. All communication through the order chat or the system-sent resolution message. Keeps audit trail intact.
- ❌ Don't promise a specific timeline in the resolution message ("I'll get back to you in 2 hours"). Use "Resolution pending — expect an update within 48 hours" if you need to stall.
- ❌ Don't resolve a dispute without reading the full order conversation. You will miss the critical detail 60% of the time.
- ❌ Don't use emojis in admin_notes. Future admins (and potentially auditors) need to parse it without ambiguity.
- ❌ Don't resolve disputes for orders where you're personally connected to either party. Hand it to another admin.
- ❌ Don't edit or delete evidence files uploaded by either party. If anything looks like it violates TOS, flag it — don't quietly remove.

---

## Escalation path

If this runbook doesn't cover what you're looking at:

1. Post in admin Discord channel with the dispute ID and what's unusual
2. Tag all 3 admins if nobody's online
3. For legal/compliance cases (fraud, IP claims, payment-card disputes going to chargeback): email `support@kaasb.com` and cc Dr. Mustafa (`mustafaalnasiry21@gmail.com`)

---

## Backlog items tracked against this runbook

- [ ] Phase 4: QiCard v1 3DS refund API → programmatic refunds instead of manual portal transfers (will simplify Step 4 refund path)
- [ ] Post-launch: partial-split resolutions (e.g., 60/40) — currently not supported in code; workaround is refund + separate manual transfer
- [ ] Post-launch: mandatory cooldown before a client can dispute again on the same freelancer
