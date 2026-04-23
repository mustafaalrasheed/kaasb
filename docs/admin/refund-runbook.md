# Refund Runbook

How a Kaasb admin returns IQD to a client. **Every refund is manual today** — QiCard's v0 API has no refund endpoint (we use v0 for payments; the v1 3DS API has refunds but we haven't migrated yet — Phase 4 work tracked as Known Issue #2). Until Phase 4 ships programmatic refunds, refunds are portal-driven.

Last updated: 2026-04-23. Maintainer: Mustafa Alrasheed.

> ⚠️ **Status: QiCard portal sections are placeholders.** The Kaasb-side triggers and audit flow are fully documented. The QiCard portal click-path for actually moving IQD back is marked `[PENDING QICARD PORTAL WALKTHROUGH]`. A 10-minute walkthrough from the user on 2026-04-24 will fill these in. Until then, follow the Kaasb-side steps exactly and extrapolate the portal part.

---

## Scope

This runbook covers:

- Refunds on an active order (escrow is `FUNDED` or `DISPUTED`) — the expected 80% of refund cases
- Post-completion refunds (rare, requires override — the other 20%)
- Refunds triggered by a dispute resolution (`resolution="refund"`)

This runbook does **not** cover:

- Releasing escrow to a freelancer (opposite direction) — see [payout-runbook.md](./payout-runbook.md)
- Chargebacks originating from the cardholder's issuing bank — different flow, legal/compliance territory, escalate to Mustafa
- Void (pre-settlement cancellation) — see "Void vs refund" section below

---

## Refund types at a glance

| Scenario | Who triggers | Escrow state at start | Where in flow |
|----------|--------------|----------------------|---------------|
| Client cancels PENDING order | Client self-service | `PENDING` | Auto-cancel + auto-refund; no admin needed |
| Stale PENDING >30min | Cron (`expire_stale_pending_orders`) | `PENDING` → none | Auto-cancel; QiCard charge never captured |
| Dispute resolved with `refund` | Admin (dispute runbook) | `FUNDED` / `DISPUTED` → `REFUNDED` | This runbook (Steps 1-5) |
| Post-completion refund (manual override) | Admin | `RELEASED` → `REFUNDED` | This runbook + Mustafa approval |
| Duplicate charge / QiCard error | Admin | Transaction exists but no escrow | This runbook (out-of-band path) |

---

## Prerequisites

- Admin logged into https://kaasb.com/admin
- Admin logged into the QiCard merchant portal
- The underlying order/escrow clearly identified — you need the order ID and the original Qi Card `paymentId` (stored in `transactions.qi_card_payment_id` once Phase 4 migration adds the column; currently stored in the transaction's provider ref)
- For post-completion refunds: written approval from Mustafa in the admin Discord, documented in the refund's Admin Notes

---

## Step 1: Understand why you're refunding

Every refund needs a clear-written reason. Before touching anything:

- **Is this the outcome of a formal dispute?** → Confirm the dispute resolution is recorded + `resolution="refund"`. Proceed.
- **Is this a support-triggered refund on an active order?** → Confirm you've checked per [support-runbook.md](./support-runbook.md); ideally escalate to a formal dispute first (auditability); only bypass if the case is clear-cut (e.g., double-charged duplicate payment).
- **Is this post-completion?** → Stop. Double-check with Mustafa before proceeding. Post-completion refunds set bad precedent; they require explicit owner approval.

Write the reason in plain text — you'll paste it into Admin Notes later. "Client charged twice for order XYZ due to retry on payment-result timeout (see Sentry issue ABC)" is good. "Refund" is not.

## Step 2: Find the escrow + lock it

1. Admin panel → **Orders** tab → search by order ID or client email
2. Click the order → you see the escrow card + transaction history
3. If escrow is `FUNDED` or `DISPUTED` → proceed
4. If escrow is `RELEASED` or `REFUNDED` already → stop. `RELEASED` means money already went to freelancer; that's a dispute or post-completion case, not a standard refund. `REFUNDED` means it's already done.
5. If escrow is `PENDING` — the client hasn't actually paid yet; no refund to issue

## Step 3: Record the refund intent in Kaasb FIRST

**Before touching the QiCard portal**, record what you're about to do in Kaasb:

1. In the order detail view, click **"Issue Refund"**
2. Fill in:
   - **Amount** — typically the full escrow; partial refund field available for edge cases
   - **Reason** — from Step 1; be specific
   - **Related Dispute ID** — if this refund is from a dispute resolution
3. Click **Mark as Pending Refund**

This sets:
- `escrow.status = REFUND_PENDING` (conceptual — prevents concurrent actions)
- Creates a `Transaction` row of type `REFUND` in pending state
- Writes an audit log entry

**Why record first, then transfer?** If the QiCard transfer succeeds but Kaasb crashes before Step 5's Confirm, you have proof of intent. If the transfer fails, the pending record is easy to cancel. Doing it the other way (transfer first, record second) risks real money moved with no Kaasb trace.

## Step 4: Execute refund in QiCard merchant portal

**Every refund today is a manual portal action.** `qi_card_client.refund_payment()` in the backend raises `QiCardError("no refund API available in v0")` intentionally — this is working as designed until Phase 4.

> `[PENDING QICARD PORTAL WALKTHROUGH — to be filled on 2026-04-24]`
>
> Needs answers to:
>
> - Is there a "Refund" action per-transaction in the portal, or is it done as a reverse transfer via the client's phone/identifier?
> - If per-transaction: where in the UI? (Transaction history → select → "Refund"?)
> - If reverse transfer: what identifier? (Client's `qi_card_phone`? Original payment's `paymentId`? Client's name on card?)
> - What fields does the form require?
> - Can we do partial refunds, or is it all-or-nothing?
> - Does the refund appear on the client's QiCard as a reversal (negative on original charge) or as a new incoming transfer? **Big deal** — affects what the client sees on their statement + what we tell them in communications.
> - What reference does the portal give us (refund transaction ID)?
> - Timing: is it immediate, minutes, hours?
> - Fees charged to merchant on refunds?

Until the walkthrough is complete: do **not** guess the path. If you need to issue a refund before 2026-04-24, contact QiCard merchant support directly at `qicard@qi.iq` / `+964 771 640 4444` — they can walk you through live.

**When executing:**
- Match the Kaasb refund amount exactly
- Use the original payment's identifier as the basis (if the portal has a transaction-history-based refund)
- Save the **refund transaction reference** immediately after confirming — you need it for Step 5

## Step 5: Confirm Refund in Kaasb

Return to the order:

1. Click **"Confirm Refund Completed"**
2. Fill in:
   - **QiCard Refund Transaction Reference** (ref from Step 4)
   - **Admin Notes** — anything unusual
3. Click **Confirm**

Behind the scenes:
- `escrow.status = REFUNDED`
- `transactions.status = SUCCESS` (the refund transaction)
- `order.status = CANCELLED` (if not already)
- Notification to client: "Your refund of X IQD has been processed."
- Audit log entry

## Step 6: Communicate with client

The automated notification is a starter — but for non-trivial refunds, send a personal message:

- **Acknowledge what happened**: "We've refunded your payment for order #XYZ."
- **State timing**: "Depending on your bank, it may take [timing from Step 4] for the funds to appear in your QiCard."
- **Include the refund reference**: "QiCard refund reference: [ref]"
- **If a dispute drove it**: "The dispute was resolved in your favor per the evidence provided."
- **If it was a platform error**: apologize directly. "This was our mistake, not yours. We've fixed [underlying issue]."

---

## Common scenarios

### Scenario A: Dispute resolved with refund

1. Dispute runbook was followed — `resolution="refund"` set
2. Escrow is already in `DISPUTED` state
3. Follow Steps 2-6 here, with **Related Dispute ID** filled in Step 3

### Scenario B: Duplicate charge

Client got charged twice for the same order because:
- Client clicked "Pay" twice before Qi Card redirect completed, OR
- Our webhook retry logic double-counted a transaction

Steps:
1. Identify the duplicate via `transactions` table — two rows for the same order, both succeeded
2. The FIRST charge funded the escrow; the SECOND is stranded (no associated escrow)
3. For the second (stranded) charge: refund without touching the order. Use the "Issue Standalone Refund" flow in admin → Transactions tab → select the duplicate → Refund.
4. Fill in Step 3 + 4 + 5 as above, noting "Duplicate of transaction #XYZ, stranded due to webhook race."

### Scenario C: Post-completion refund (goodwill)

Client paid, order completed, escrow released to freelancer, freelancer already got paid via QiCard. Client comes back weeks later with a genuine complaint.

Kaasb policy: **not automatic**. Must be approved by Mustafa.

If approved:
1. Refund from Kaasb's merchant balance (not from freelancer's account — we can't claw back from their QiCard)
2. Steps 3-6 as above, with Admin Notes: "Goodwill refund post-completion, approved by Mustafa on [date] per Discord thread [link]. This is Kaasb absorbing the cost; freelancer keeps the earlier payout."
3. `escrow.status` stays `RELEASED` (it was already); an "ADJUSTMENT" transaction is created separately

### Scenario D: Partial refund

Client received partial value (e.g., the freelancer delivered 3 of 5 promised items). Dispute resolved with a split.

**Kaasb doesn't natively support splits today** — dispute resolution is binary (refund-all or release-all). Workaround:

1. Resolve dispute with `release` (freelancer gets full escrow)
2. Separately refund the client a portion from Kaasb's merchant balance (same as goodwill flow in Scenario C)
3. In Admin Notes on both transactions, cross-reference so audit trails match

This is clumsy. Phase 11+ backlog: proper partial-resolution in the dispute flow.

### Scenario E: Client's QiCard is closed / blocked

- QiCard portal attempts refund → "destination not available"
- Options:
  1. Wait — if the card is temporarily blocked, it'll unblock (ask client their timeline with QiCard)
  2. Ask client for an **alternative payout destination** (another QiCard in their name, bank account) — treat carefully, verify identity
  3. If card is permanently closed: escalate to QiCard merchant support; they may be able to bridge via an escrow account
- Do NOT refund to a different person's account

---

## Void vs refund

If a payment has **not yet been captured** (pre-settlement), we can **void** it instead of refund. Void:

- Reverses the authorization before funds actually move
- No fee from QiCard
- Client's card shows a pending-then-vanishing charge (not a refund)

Whether this applies depends on timing: QiCard's v0 API charges appear to capture immediately (no auth-capture split), so void is likely not an option on this integration. The `mars-iq/iq-epay` wrapper has a `QiVoidOrder()` method suggesting it exists — but we haven't integrated it.

**Practical rule until confirmed:** treat all Kaasb payments as already captured. Always do refunds, never voids. Revisit post-walkthrough if QiCard confirms void is viable.

---

## Edge cases

- **Refund > original payment amount** — shouldn't be possible via UI (form caps at escrow amount). If requested (e.g., "and pay us our lost interest"), that's a goodwill issue, not a refund — separate transaction.
- **Refund in a different currency** — never. IQD only. Kaasb is IQD-native per Known Issue #5 resolution.
- **Refund straddles a QiCard fee reconciliation period** — if QiCard deducted fees from the original charge but doesn't credit them back on refund, the merchant account eats the fee. Track these in monthly reconciliation; if material, raise with QiCard.
- **Refund on a Transaction where `qi_card_payment_id` is missing** — older transactions from v0 API integration may not have this field populated. Portal refund requires the original payment reference — if you can't find it, QiCard support can look it up by amount + date + client phone.

---

## Don't do list

- ❌ Don't refund before recording intent in Kaasb (Step 3 before Step 4, always). Untracked portal refunds are audit disasters.
- ❌ Don't refund to a different user than the one who paid. Even if they ask. Even if they're family. Refund goes to the original payer; if they want to transfer to someone else, that's their business after the refund lands.
- ❌ Don't "batch" refunds by doing one big QiCard transfer to cover multiple client refunds. One refund transaction per client, per order.
- ❌ Don't delete or edit Transaction rows. If you made a mistake, issue a corrective transaction.
- ❌ Don't respond to a client with a refund timeline you're not certain about. "Typically within X [timing]" with a source (QiCard portal docs, not guesses).
- ❌ Don't refund without finding and citing the original `paymentId`. If you can't find it, pause and ask for help.

---

## Troubleshooting quick table

| Symptom | Check | Fix |
|---------|-------|-----|
| "Issue Refund" button not visible | Escrow status | Must be FUNDED or DISPUTED; RELEASED means already paid out, REFUNDED means done |
| Portal refund rejects | Destination card state | Contact QiCard support; confirm client's card is active |
| Kaasb shows REFUNDED but client says no money | QiCard settlement lag | Wait [timing]; verify via portal transaction history; if still missing after window, escalate to QiCard |
| Refund amount doesn't match transaction | Fee deduction by QiCard on original charge | Document in Admin Notes; monthly reconciliation |
| Multiple refunds queued | Merchant balance drop | Review batch; pause if balance insufficient; notify Mustafa |

---

## Backlog items

- [ ] **Phase 4 (Known Issue #2)**: migrate to QiCard v1 3DS API → programmatic refunds via `POST /api/v1/payment/{paymentId}/refund`. Once shipped, Steps 4 becomes a single API call and Steps 3+5 merge into one Kaasb action.
- [ ] **Weekly reconciliation** (Phase 12): script that diffs QiCard portal transaction history against Kaasb `transactions` — catches any missed refunds or orphaned merchant-account deposits.
- [ ] **Partial refund support in Dispute model** (post-launch): remove the binary resolution constraint so splits can be first-class.
- [ ] **Client refund timeline visibility in UI** — today the client sees "Refund processed" but no ETA for when it hits their QiCard. Surface the typical timing (once we know it from the walkthrough).

---

## After Phase 4 ships

Once `refund_payment_v1()` is wired (per plan Phase 4), this runbook's Step 4 becomes:

1. Click "Issue Refund" (Step 3)
2. Kaasb backend calls QiCard v1 API automatically
3. Refund processed end-to-end within seconds
4. Step 5 ("Confirm") is folded into Step 3 — no manual confirmation needed

The QiCard portal walkthrough will still matter for fallback mode when the v1 API is unavailable.
