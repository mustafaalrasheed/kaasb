# Manual Payout Runbook

How a Kaasb admin gets IQD into a freelancer's QiCard after an order completes. Kaasb has **no payout API** (QiCard doesn't publish one — confirmed per [project_qicard_api_surface.md](../../../.claude/projects/c--Users-Mustafa-Alrasheed-Desktop-kaasb/memory/project_qicard_api_surface.md) memory + the published [developers-gate.qi.iq](https://developers-gate.qi.iq/) surface). Every payout is a manual QiCard merchant portal transfer followed by a "Confirm Payout" click in Kaasb admin.

Last updated: 2026-04-23. Maintainer: Mustafa Alrasheed.

> ⚠️ **Operational reality (2026-04-24):** QiCard does not currently have a merchant portal we can access. Payouts are executed through the **QiCard mobile app** using the freelancer's QiCard phone number (and optionally their holder name as a visible reference on the transfer). The Kaasb API key in `.env.production` is for the **client-side payment gateway** (`create_payment` v0 endpoint) — it does NOT perform payouts. The app transfer is always a manual admin action.

---

## Scope

This runbook covers:

- Releasing a single escrow for a single freelancer
- Both standard-flow (escrow <500k IQD, one-click) and dual-control (escrow ≥500k IQD, two admins)
- Post-transfer reconciliation in Kaasb

This runbook does **not** cover:

- Refunds back to clients — see [refund-runbook.md](./refund-runbook.md)
- Bulk payout batching — not currently supported in Kaasb; one escrow at a time
- Resolving a dispute before payout — see [dispute-runbook.md](./dispute-runbook.md) first

---

## Prerequisites

Before starting a payout session:

- You're logged into `https://kaasb.com/admin`
- You're logged into the QiCard merchant portal (credentials in the shared password vault — see `decision-log.md`)
- The freelancer has **both** `qi_card_phone` and `qi_card_holder_name` set on their `payment_accounts` row (Kaasb will block release otherwise, per [release_escrow_by_id](../../backend/app/services/payment_service.py))
- The escrow is in `RELEASED` status (escrow has been unlocked from the order completion; funds are conceptually owed to the freelancer but not yet transferred)

---

## Cadence recommendation

**Suggested payout schedule**: Tuesday and Friday, ~10:00 Baghdad time. Batch all pending payouts from the previous 3-4 days. This:

- Gives freelancers a predictable rhythm (they learn when to expect payouts)
- Limits admin time spent context-switching
- Keeps dual-control approvals bunched so whoever's the second admin can approve several at once

You can still process individual payouts off-cadence for special cases (e.g., freelancer needs it urgently).

---

## Step 1: Find pending payouts

1. Admin panel → **Payouts** tab
2. Default view: "Pending Payouts" — lists every `escrow.status = RELEASED` that hasn't been marked paid yet
3. Sort by oldest first (FIFO — freelancers who waited longest get paid first)

Each row shows:

- Freelancer name + avatar
- Amount (IQD, after the 10% platform fee already deducted)
- Order ID the escrow belongs to
- Release timestamp
- QiCard account info: `qi_card_phone`, `qi_card_holder_name`
- "Release" button (enabled only if both QiCard fields are filled)

If the freelancer's QiCard fields are missing, the button is disabled. Before you can pay them, email them a link to `/dashboard/payments` to finish their payout account setup. Don't bypass this — the `qi_card_holder_name` is required for the merchant portal lookup.

## Step 2: Verify the amount + dual-control

| Amount | Flow |
|--------|------|
| < 500,000 IQD | Single-admin — you can click Release + confirm |
| ≥ 500,000 IQD | **Dual-control** — you click "Request Release"; a different admin must approve via the **Payout Approvals** tab before the transfer happens |

The threshold is `PAYOUT_APPROVAL_THRESHOLD_IQD` in config (default 500,000 per the decision log). `PayoutApprovalService.request_release` enforces this; you can't bypass it in the UI.

**The admin who requests release cannot also approve it** — the backend blocks this via `requester_id` check. One of the other admins must do the approval click.

## Step 3: (Dual-control only) Wait for / coordinate approval

If you requested a ≥500k payout:

1. The escrow sits in `pending_second_approval` state
2. The other admins see it in the **Payout Approvals** tab
3. Ping the other admin in admin Discord — include the escrow ID + freelancer name
4. They review the underlying order (was it completed cleanly? any disputes?) + click **Approve**
5. Once approved, `PayoutApprovalService.approve` calls `release_escrow_by_id` internally — the escrow is now ready for you to transfer

If the other admin **Rejects**, escrow goes back to `RELEASED` state but is flagged. Read their rejection notes and address the concern — often means "I think this needs dispute review first."

## Step 4: (Sub-threshold only) Click Release

For payouts under the threshold: click **Release** → confirm → escrow is ready for transfer. One click, no second admin. An audit log entry is written automatically.

## Step 5: Transfer IQD via the QiCard mobile app

**This is the manual part.** Every payout is executed on the admin's phone using the QiCard app — there is no merchant portal available to Kaasb at this time, and the QiCard v0 API does not expose a payout endpoint. The app is the only transfer path.

**Principles before you start:**

- Match the IQD amount Kaasb showed you **exactly** — to the whole Dinar.
- Use the `qi_card_phone` from the Kaasb Payouts row as the transfer destination.
- Paste the freelancer's `qi_card_holder_name` into the QiCard app's "note" / "reference" / "memo" field (whichever label it uses) so the transfer is auditable after the fact.
- Keep the QiCard transaction reference the app gives you on confirmation — you'll paste it into Kaasb in Step 6.
- **Never split one Kaasb escrow into multiple QiCard transfers** unless the per-transaction limit forces it. If it does, record every ref in Admin Notes.
- Do **not** transfer from a personal QiCard account. Always use the dedicated Kaasb merchant/admin QiCard.

**Click path in the QiCard app** (may evolve between QiCard releases — update this section when it does):

1. Open the QiCard app on the admin phone → log in with PIN / biometric
2. Select the Kaasb merchant/admin account (if the app presents multiple accounts)
3. Tap **Transfer** (or the local-language equivalent)
4. Enter destination:
   - **Mobile number** field: paste `qi_card_phone` from the Kaasb row (include the `+964` prefix if the app expects international format)
   - The app usually resolves the destination account and shows the cardholder's name. **Verify it matches** `qi_card_holder_name`. If it doesn't, STOP — the freelancer may have typed a wrong phone. Don't transfer.
5. **Amount** field: enter the IQD amount exactly as shown in Kaasb Payouts (the `freelancer_amount` column, which is 90% of the escrow after the 10% platform fee).
6. **Note/Reference/Memo** field: enter something traceable, e.g. `Kaasb payout escrow-<id>` or just `Kaasb payout <freelancer first name>`. This appears on the freelancer's QiCard statement.
7. Confirm the transfer (the app may require an OTP / PIN / biometric re-auth).
8. On the confirmation screen, copy the **Transaction reference** (usually a 10-14 digit number or alphanumeric ID). You can screenshot the receipt too — save it to the shared admin drive.

**Known unknowns** to verify during the first few real payouts and then record here:

- Per-transaction / per-day limit on the merchant account (app usually displays this before confirm)
- Fees charged to the sender vs. receiver
- Timing: seconds or up to a few minutes for the receiver's balance to reflect
- What the app shows if the destination phone is invalid or card is blocked

If you hit any of the unknowns, record the actual behaviour in Admin Notes and in a follow-up PR to this runbook.

## Step 6: Confirm Payout in Kaasb admin

Back in Kaasb:

1. Return to the escrow in the **Payouts** tab
2. Click **"Confirm Payout"** on the same row
3. Fill in:
   - **QiCard Transaction Reference** (the ref/receipt ID from the portal)
   - **Admin Notes** (optional) — use for anything unusual (e.g., "took 2 transfers due to limit; refs XYZ + ABC")
4. Click **Confirm**

Behind the scenes:
- `escrow.status` remains `RELEASED` but gets `paid_out_at = now()` + `qi_card_transaction_ref = <your ref>`
- A `Transaction` row is created of type `PAYOUT` with the ref
- `payment_accounts.last_payout_at` is updated
- Freelancer gets an in-app notification + email: "Your payout of X IQD has been sent to your QiCard."
- Audit log entry (via `AuditService`) records the event

## Step 7: Verify + communicate

- Spot-check the freelancer's balance in admin within 30 minutes — should show the escrow as paid
- If the freelancer asks where their money is: "Transferred via QiCard on [date] — ref XYZ. Should land in your QiCard balance within [timing from Step 5]. If not, contact support and include the ref."

---

## Common scenarios

### Scenario A: Freelancer's `qi_card_holder_name` is missing

- **Kaasb blocks the payout** — "Release" button is disabled on the row
- Email the freelancer a short message: "Please visit https://kaasb.com/dashboard/payments and fill in your cardholder name to receive payouts."
- Don't override this in the backend. The field exists specifically because the QiCard portal matches on it (name-on-card).

### Scenario B: QiCard transfer succeeded but Kaasb Confirm Payout was missed

- The freelancer got paid, but Kaasb still shows the escrow as pending
- Pull the QiCard reference from the portal's transaction history
- Enter it in "Confirm Payout" now with a note: "Payout executed [date] but confirmation step was missed; recording retroactively"
- Tell the freelancer apologetically: money is with them, Kaasb's bookkeeping is catching up

### Scenario C: QiCard transfer failed but merchant balance dropped

- Screenshot the portal transaction + error
- Do NOT click Confirm Payout in Kaasb
- Email qicard@qi.iq or call +964 771 640 4444 with the attempted transaction details
- Re-attempt the transfer after QiCard's resolution
- If funds are still debited from merchant, this is a QiCard-side dispute — escalate to Mustafa

### Scenario D: Duplicate payment attempt

- You clicked Confirm Payout twice; second click failed
- Kaasb's `release_escrow_by_id` is idempotent via the `paid_out_at` check — no double-pay risk on Kaasb side
- QiCard side: the portal prevents same-ref-number duplicates but does NOT auto-detect same-destination-same-amount duplicates — be careful with the back button

### Scenario E: Amount mismatch between Kaasb and QiCard transfer

- If you accidentally transferred the wrong amount in QiCard, do NOT "adjust" in Confirm Payout
- Send a corrective transfer (either return-to-merchant-account or supplement) via the portal
- Record both refs in Admin Notes on the escrow
- Explain to the freelancer if it affects their balance

### Scenario F: Freelancer changed `qi_card_phone` after the escrow was released but before you paid out

- The `payment_accounts.qi_card_phone` that Kaasb shows is the **current** value, not the value at time of release
- Always read the phone/cardholder name from the row at the moment of transfer — never from memory
- If the freelancer changed it maliciously (attempted fraud), `payment_accounts` history should show the change timestamp; escalate

---

## Edge cases

- **Freelancer has a name-on-QiCard that includes characters not in their Kaasb profile display name** — the QiCard portal is the source of truth; always transfer to the exact name they specified in `qi_card_holder_name`, not their display name.
- **Transfer limit exceeded** — the portal enforces per-transaction limits (we'll document in Step 5 after the walkthrough). If an escrow exceeds a single-transfer limit, split into multiple transfers + log all refs in Admin Notes.
- **Merchant balance below escrow amount** — shouldn't happen with normal order flow, but if it does: escalate immediately. Probably a webhook or reconciliation gap.
- **Escrow released via dispute resolution** — same flow. But double-check that the dispute resolution note doesn't say "refund" — clicking Release on a dispute-refund escrow is a serious mistake.
- **Beta freelancer testing** — sometimes during testing we may want to "pretend" to pay without real IQD movement. **Don't do this**. Either cancel the order entirely or process a real (small-amount) transfer. Dry-runs corrupt the audit trail.

---

## Dual-control flow (diagram)

```
[Admin A] Pending Payouts tab
    ↓ clicks "Request Release"
[Backend] PayoutApprovalService.request_release(escrow_id, admin_A)
    ↓ amount ≥ 500k IQD → creates PayoutApproval (status=pending)
[Admin B] Payout Approvals tab
    ↓ clicks "Approve"
[Backend] PayoutApprovalService.approve(approval_id, admin_B)
    ↓ admin_B != admin_A (enforced) → release_escrow_by_id runs
[Admin A] back to Pending Payouts tab
    ↓ clicks "Release" (now unblocked)
    ↓ manually transfers IQD via QiCard portal (Step 5)
    ↓ clicks "Confirm Payout" with ref (Step 6)
[Done]
```

---

## Don't do list

- ❌ Don't manually flip `escrow.paid_out_at` or `payment_accounts.last_payout_at` in the database. Use the admin UI's "Confirm Payout" — it creates the Transaction + audit entry.
- ❌ Don't transfer via a personal QiCard account. All payouts must go through the merchant account.
- ❌ Don't combine multiple freelancer payouts into one QiCard transfer. Even if they total under a limit, the portal reference can only tag one Kaasb escrow.
- ❌ Don't approve your own `Request Release` via the dual-control path. Backend blocks this; if you see the button enabled, something's wrong — report in admin Discord.
- ❌ Don't confirm a payout without an actual QiCard transaction reference. Fake refs destroy auditability.
- ❌ Don't pay out an escrow that's under active dispute. `escrow.status` should be `RELEASED` not `DISPUTED` when you click Release.

---

## Backlog items

- [ ] Phase 4: QiCard v1 3DS refund API → irrelevant to payouts (no v1 payout API exists) but might hint at future transfer APIs — watch the release notes
- [ ] Post-launch: batch payouts (one click → multiple transfers) — requires either a new QiCard API (unlikely) or careful one-by-one orchestration
- [ ] Post-launch: auto-notify freelancer when QiCard transaction ref is confirmed (already in place)
- [ ] Phase 12: weekly reconciliation script — compare QiCard merchant portal transaction history vs Kaasb `transactions` table, flag mismatches

---

## Troubleshooting quick table

| Symptom | Check | Fix |
|---------|-------|-----|
| "Release" button disabled | `qi_card_phone` / `qi_card_holder_name` on row | Email freelancer to fill setup form |
| "Request Release" always required, amount is small | Check `PAYOUT_APPROVAL_THRESHOLD_IQD` in `.env` | If 0, threshold is set to "all dual-control" — intentional for audits or bug |
| QiCard portal rejects destination | Phone format wrong, or card blocked | Verify phone format; contact QiCard support for card state |
| Kaasb "Confirm Payout" button 500s | Check Sentry | Likely DB constraint; don't retry — fix first |
| Transfer succeeded, freelancer says "not received" | Check QiCard transaction status via portal | If "Success" on portal but freelancer still says no — ticket with QiCard |
