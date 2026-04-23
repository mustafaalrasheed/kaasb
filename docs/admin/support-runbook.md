# Support Triage Runbook

How a Kaasb admin handles an incoming support ticket — from notification through resolution. Use this for general support (account questions, payment confusion, bug reports). For formal marketplace disputes, use [dispute-runbook.md](./dispute-runbook.md).

Last updated: 2026-04-23. Maintainer: Mustafa Alrasheed.

---

## Scope

Tickets in Kaasb arrive through two channels:

1. **In-app**: user clicks "Contact Support" on `/dashboard/messages` → opens a `ConversationType.SUPPORT` thread addressed to all admins
2. **External email**: user emails `support@kaasb.com` → delivered to all 3 admin inboxes

This runbook covers both channels. In-app is preferred because it auto-binds the user's identity + browser context; external email requires manual user identification.

**Do NOT** use this runbook to:
- Resolve a formal dispute — use [dispute-runbook.md](./dispute-runbook.md)
- Initiate a payout or refund — those have their own runbooks
- Handle legal notices or chargebacks — escalate to `support@kaasb.com` and cc Dr. Mustafa personally

---

## Prerequisites

- Admin account on kaasb.com (`is_superuser=True`) OR support staff (`is_support=True`)
- Access to `support@kaasb.com` forwarded inbox
- Read access to the admin panel
- If you're responding from outside the in-app flow (e.g., email reply), you still need to log the outcome in Kaasb — see "Closing" below

---

## SLA targets

| Channel | First response | Resolution |
|---------|----------------|------------|
| In-app SUPPORT thread | ≤ 8 business hours (08:00–20:00 Baghdad time) | ≤ 48 hours |
| `support@kaasb.com` email | ≤ 8 business hours | ≤ 48 hours |
| Dispute escalated from support | Claim within 4 hours → see dispute-runbook | Per dispute-runbook |

"Business hours" = 08:00–20:00 Baghdad time, 7 days a week. Overnight tickets acknowledged next-morning.

These are published to users on `/help` + the privacy footer. Don't overpromise by responding faster for one person — we can't sustain that.

---

## Step 1: Claim the ticket

All three admins see every new SUPPORT thread. **First to respond owns it** — this prevents double-replies.

1. Open https://kaasb.com/admin → **Support** tab
2. Under "Unassigned", pick the oldest ticket first (FIFO)
3. Click **"Claim"** — this sets `support_assignee_id = your_user_id` via `message_service.claim_support_ticket`
4. Other admins now see it as claimed; you're the only one actively driving it

If you claim and can't resolve within your window (e.g., about to go offline), click **"Release"** — it goes back to Unassigned for someone else. Never leave a claimed ticket orphaned.

## Step 2: Identify the user

Even for in-app tickets, do a 30-second identity check:

- Which user role? (Client, freelancer, or both?)
- Account verified? Phone OTP confirmed? Email confirmed?
- Any open orders / disputes / payouts at this moment?
- When did they register? Any prior support tickets?
- Any `chat_violations` or `chat_suspended_until` flags?

The admin Support-tab sidebar shows most of this automatically. For email tickets, search by email in the admin Users tab first.

## Step 3: Categorize

Label the ticket with one of these 7 categories. This is for your own decision-making + logging; the user doesn't see the label.

| Category | Typical examples | First action |
|----------|------------------|--------------|
| **Account** | Can't log in, OTP not arriving, password reset, email change | See macros for the specific issue |
| **Payment (client)** | Payment didn't go through, wrong amount charged, duplicate charge | Check `transactions` table via admin → Payments; walk through status |
| **Payment (freelancer)** | Payout not received, when will I get paid, how to set up QiCard | See [payout-runbook.md](./payout-runbook.md); confirm `payment_accounts.qi_card_phone + qi_card_holder_name` are filled |
| **Order** | "Freelancer disappeared" / "Client is unresponsive" / "Scope changed" | If escrow is funded + order not yet complete → consider escalating to dispute (see below) |
| **Bug / platform** | Upload fails, page won't load, chat broken | Reproduce if possible; file Sentry/Github issue; respond with workaround |
| **Feature request** | "Can you add X?" | Log to backlog; polite "on our roadmap" reply; don't overpromise |
| **Other** | Press questions, legal notices, TOS clarifications | Escalate to Dr. Mustafa personally |

## Step 4: Respond

Use the canonical response macros from [support-macros.md](./support-macros.md) — they're bilingual (AR/EN) and tuned to the most common 8 question types. Adapt, don't copy-paste verbatim; the user should feel heard.

Standards:

- **Always use the user's name** (from their profile)
- **Match the language the user wrote in** — if they wrote in Arabic, reply in Arabic. If mixed, reply in whichever they used more.
- **Be specific** — cite the order ID, transaction ref, or dispute ID if relevant. Generic replies erode trust.
- **Never share another user's private data** — don't forward the freelancer's message thread to the client verbatim; describe and summarize if needed.
- **Never promise a refund you haven't actually issued** — once you say "we'll refund you today", it must happen today. Under-promise, over-deliver.

## Step 5: Take action (if needed)

If resolving the ticket requires a platform action — release an escrow, cancel an order, issue a refund, reset a password — **do the action in Kaasb admin, not verbally via chat**. Every platform change has an audit trail; chat promises do not.

Common actions and where to take them:

| Action | Where in admin |
|--------|---------------|
| Reset user password | Users tab → user row → "Send reset link" |
| Clear a chat suspension (`chat_suspended_until`) | Users tab → user row → "Unsuspend chat" |
| Cancel a stuck order | Admin → Orders → find order → Cancel (requires approver for >500k IQD) |
| Promote / demote admin | Users tab → "Toggle Admin" (requires confirm; see dual-control threshold memory) |
| Issue a manual refund | [refund-runbook.md](./refund-runbook.md) |
| Unlock an escrow | [payout-runbook.md](./payout-runbook.md) |

## Step 6: Escalate to a formal dispute when warranted

A support ticket becomes a dispute when:

- The user wants a **refund of escrow funds** on an active order (not a completed one)
- The dispute is between two parties (client vs freelancer) and requires adjudication
- The user explicitly says "I want to open a dispute" or equivalent
- Evidence files need to be collected from both sides

To escalate: guide the user to use the in-app **"Open Dispute"** button on their order, which creates a proper `Dispute` record. Don't try to "resolve the dispute" from the support thread — the dispute model captures evidence + both-sides structured, which the support thread doesn't.

If the user has already posted their complaint in support, also: copy the key claim + any evidence links into the dispute's `admin_notes` so whoever picks up the dispute isn't starting from zero.

Once the formal dispute is open, the support thread can be closed with "You've opened dispute #XYZ — the team will reply there within 48 hours."

## Step 7: Close the ticket

When resolved:

1. Send a final message confirming what was done (e.g., "Password reset link sent; let us know if it doesn't arrive in 5 minutes")
2. Click **"Release"** — clears `support_assignee_id`, returns the ticket to the pool, and tagged as closed in the UI
3. One-line summary in the admin Discord `#support` channel: `[SUP-xxx] category | user | outcome` (e.g., `[SUP-42] Payment-client | @client123 | Duplicate charge resolved, partial refund issued`)
4. If the ticket produced a bug: file a GitHub issue; reference the ticket ID in the issue body

Never close a ticket silently. The user should always see a final message.

---

## Common scenarios

### Scenario A: "I can't log in"

1. Verify the user exists (Users tab → search by email/phone)
2. Check status — if `chat_suspended_until` is active, they CAN still log in (that's just chat-restricted); otherwise proceed
3. Check `is_email_verified` — if false, resend verification email
4. If they say "wrong password", send password reset link (don't tell them their password — we don't know it)
5. If they say OTP not arriving, check the Twilio chain: WhatsApp → SMS → email. If email also missing, check Resend logs; also tell them to check spam.

### Scenario B: "I paid but my order is stuck at pending"

1. Find the order (Admin → Orders → search by ID or client email)
2. Check escrow status:
   - `PENDING` — payment not yet confirmed by Qi Card. Check `transactions` table for Qi Card status. If `SUCCESS`, manually flip to `FUNDED` + `order.status → IN_PROGRESS` (rare — usually auto-handled by webhook). If still `PENDING` after 10 min, payment didn't complete; user should retry.
   - `FUNDED` — order is live; reassure the user the freelancer will respond
   - `DISPUTED` / `REFUNDED` — a dispute/refund already happened; explain status
3. If client paid but order was auto-cancelled by the F7 stale-order cron, the escrow auto-refunds. Confirm refund hit their Qi Card.

### Scenario C: "When will I receive my payout?"

1. Confirm freelancer has `payment_accounts.qi_card_phone` + `qi_card_holder_name` filled. If not, send to `/dashboard/payments` setup form.
2. Check "available balance" on their payment dashboard = sum of released escrows not yet paid out
3. Explain: Kaasb admins manually transfer IQD via the QiCard merchant portal. Standard window: every Tuesday and Friday. Amounts >500k IQD require a second admin's approval (dual-control threshold).
4. If it's been more than a week without payout, escalate to Mustafa — shouldn't happen.

### Scenario D: "Freelancer is ghosting / Client is unresponsive"

This is a disguised dispute. Acknowledge the frustration, then:

1. Read the order's message thread to verify (not just trust one side)
2. If >72h silence + order still active → guide the user to open a formal dispute
3. Don't take sides in the support thread

### Scenario E: "Can I have a refund?"

1. What's the state of the order? (PENDING / FUNDED / COMPLETED)
2. PENDING → user can cancel themselves in-app; no admin needed
3. FUNDED + still active → open a dispute
4. COMPLETED (including auto-completed) → refunds after completion require admin override + manual QiCard reverse transfer, AND a written explanation for why (post-completion refunds set bad precedent). Escalate to Mustafa.

### Scenario F: "My OTP isn't arriving"

1. What phone number? Verify format (Iraqi mobile, country code `+964`).
2. Check the OTP delivery chain order: WhatsApp → SMS → email. For new accounts, WhatsApp or SMS should be primary; email is fallback.
3. Check Twilio logs (if Twilio creds are set) or Resend logs for the email fallback
4. If they're outside Iraq, SMS may not deliver — email fallback should work
5. If truly blocked, we can manually verify their phone via backend admin override (rare; last resort)

### Scenario G: "I was scammed by a freelancer off-platform"

Off-platform disputes are **not** within Kaasb's jurisdiction — we can only mediate what happened on-platform (in the order chat, via our escrow). Gently explain this. If the off-platform communication was **solicited from within a Kaasb order chat**, that's a TOS violation by whoever solicited — flag the user in the Admin Users tab and consider a warning/suspension.

---

## Red flags — escalate immediately

| Pattern | Escalate to |
|---------|-------------|
| Request from law enforcement / court order | Dr. Mustafa personally + legal counsel (see legal track in plan) |
| Suspected money laundering / structured payments | Pause the account, escalate to Mustafa + flag in admin chat |
| Press / journalist inquiry | Forward to Mustafa — do not respond independently |
| Claim of IP infringement (DMCA-equivalent) | Legal counsel + temporarily hide the allegedly-infringing content |
| User threatens self-harm | Provide Iraqi mental health resources + escalate to Mustafa as a welfare concern, not a support ticket |
| Multiple users reporting the same freelancer/client | Admin chat — pattern may indicate coordinated fraud |

---

## Don't do list

- ❌ Don't make promises about money movement without double-checking the escrow state in admin first
- ❌ Don't close a ticket before the user has acknowledged the resolution (give them 24h to respond to your final reply)
- ❌ Don't use emojis or casual language in payment-related tickets — professional tone
- ❌ Don't respond from a personal account or WhatsApp — all support through `support@kaasb.com` or in-app
- ❌ Don't share another user's data, screenshots, or private messages — paraphrase and redact
- ❌ Don't delete support threads — the audit trail matters if anything escalates later
- ❌ Don't try to "resolve" an active dispute from the support thread — escalate to the formal dispute flow

---

## Metrics to watch (weekly ops review)

Pull these numbers every Monday for the last 7 days:

- Tickets opened (target: <20/week at current beta volume; will grow with GA)
- Mean first-response time (target: <8h business)
- Mean resolution time (target: <48h)
- % of tickets that escalate to dispute (target: <20%)
- Top 3 categories (watch for pattern shifts — e.g., "Payment (freelancer)" surge = QiCard flow issue)
- SLA breaches — count and specific tickets (review each one: what broke, fix it)

Post the summary in admin Discord every Monday morning. Takes 5 minutes.

---

## Backlog items tracked against this runbook

- [ ] Phase 8: publish SLA commitment on `/help` page + banner — per launch plan
- [ ] Phase 8: `docs/admin/support-macros.md` — 8 bilingual canned responses
- [ ] Post-launch: auto-labeling of tickets based on user message content (ML-light classification)
- [ ] Post-launch: ticket-health dashboard in Grafana (response time heatmap, escalation rate)
- [ ] Phase 13 (mobile apps): in-app support surface parity with web
