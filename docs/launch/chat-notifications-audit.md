# Chat + Notifications System Audit

Structured audit plan of Kaasb's messaging + notifications subsystems. Opened 2026-04-24 in response to user-reported issues during beta use.

Work through each section in order; check off findings as they're resolved. Each finding links to its code location and proposed fix. **Don't treat this as a to-do list** — some findings will be "behaves-as-designed, improve UX" and others "real bug, ship a patch."

---

## Scope

**Chat subsystem covers:**
- `ConversationType` (USER, JOB, ORDER, SUPPORT) — four distinct use cases sharing the same `conversations` + `messages` tables
- WebSocket connection (Redis pub/sub cross-worker)
- Message filter (F6 anti-off-platform)
- Read receipts, typing indicators, presence
- Attachments upload + chat-specific file validation
- Support inbox + admin handlers
- Dispute system-message emission in ORDER conversations

**Notifications subsystem covers:**
- `notifications` table + 20+ `NotificationType` enum values
- In-app bell + `/dashboard/notifications` list
- Email delivery via Resend (CID-embedded logo, locale-aware templating)
- WebSocket push for real-time updates
- Per-user email opt-out (`users.email_notifications_enabled`)
- Background task dispatching via `notify_background`

**Out of scope:**
- Voice / video chat (not built)
- Group messaging (not built)
- Push to mobile apps (Phase 13)

---

## Section 1 — Confirmed findings from user reports (2026-04-24 session)

| # | Issue | Status | Fix |
|---|-------|--------|-----|
| 1 | Freelancer→freelancer DM fails with generic "Failed to send message" | **Fixed partially** | Backend rule is correct (antispam). Frontend already shows backend detail via `handleChatError` when detail is present — verified in `messages/page.tsx:351`. No further change. |
| 2 | "Failed to load messages" shows for any failure mode | **Fixed — surface backend detail** (pending push) | `fetchMessages` now distinguishes 403 / 404 / other and falls back to backend `detail` when present. See `messages/page.tsx:116`. |
| 3 | "Failed to load conversations" shows for any failure mode | **Fixed** (pending push) | Same pattern applied to `fetchConversations`. |
| 4 | Conversation badge "Support" reads as role tag on admin | **Fixed `f7c354e`** | Reworded to "Support ticket" / "تذكرة دعم" and "Order chat" / "محادثة طلب". |
| 5 | Admin has Support tag elsewhere in UI | **Needs user clarification** | Users tab in /admin filters `!u.is_superuser && u.is_support` correctly. Unclear which screen the user meant. |

---

## Section 2 — Chat — systematic review checklist

Go through one-by-one. For each, either confirm "behaves correctly" or file a finding row.

### 2.1 Conversation creation paths

- [ ] `POST /messages/conversations` with `job_id` — sender has submitted proposal OR is the job client? (rule at `message_service.py:99-121`)
- [ ] `POST /messages/conversations` with `order_id` — sender is order client or freelancer only
- [ ] `POST /messages/conversations` with no context — requires prior contract OR order between the two users
- [ ] `POST /messages/support` — creates SUPPORT conversation routed to unclaimed admin inbox
- [ ] Auto-creation: buyer request acceptance → creates USER conversation? Or stays separate?
- [ ] Auto-creation: order placement → creates ORDER conversation immediately or lazy on first message?

**Known issue:** no path for client→freelancer pre-purchase DM. Fiverr-parity gap #3 (addressed 2026-04-24: Phase 7 work item — add rate-limited pre-purchase path).

### 2.2 Message sending (`send_message`)

- [x] Filter fires on send (F6) — blocks email / phone / URL / external app names, escalates warn → block → 24h suspend. Unit tests cover the regex side; `test_chat_moderation.py` integration test confirms filter is wired in the send path.
- [ ] Attachment validation — file size, MIME type, magic bytes (reviewed `save_chat_attachment` — seems right but double-check path-traversal filename check)
- [ ] Rate limit applied per-user, per-conversation (`test_chat_scoping.py::TestMessageSendRateLimited`)
- [ ] Suspended user gets a 403 with `suspended` code + `suspended_until` + `violation_count` in response
- [ ] Message persists before WS push — if WS push fails, message isn't lost
- [ ] Sender never sees their own message as "new" via WS — verify deduplication on frontend

### 2.3 Message retrieval (`get_messages`)

- [x] Strict participant check at `get_messages:767` — staff override only for SUPPORT + ORDER types
- [x] Reading messages marks sender's messages read_at + dispatches `messages_read` WS event to sender
- [ ] Non-participant admin viewing SUPPORT thread must NOT zero out the original admin's unread counter (spot-check: `get_messages:781-787` — correctly gates by participant check)
- [ ] Pagination — verify `page_size` is clamped (messages/page.tsx fetches 50 by default)
- [ ] Ordering — messages return newest-first OR oldest-first consistently (frontend does `.reverse()` on line 125 — confirms backend returns desc)

### 2.4 Read receipts + typing indicators

- [x] Read receipts wired (messages/page.tsx:778-786) — ✓ for sent, ✓✓ sky-blue for read
- [x] Backend `_push_read_receipt` fires `messages_read` WS event to sender with `message_ids + read_at`
- [ ] Receipt update on frontend: WS handler finds message by id and flips `is_read` + sets `read_at` (line 267 — confirmed)
- [ ] Typing indicator — per-conversation membership cache + 1s rate limit on sending, 3-5s timeout on display
- [ ] Presence — `GET /messages/presence` batch endpoint, polled or WS-driven?

### 2.5 Support inbox

- [ ] Support staff (superuser OR is_support) sees unclaimed + their-own SUPPORT threads (per `claim_support_ticket` + `list_support_inbox`)
- [ ] Claim/release flow — optimistic concurrency or last-write-wins?
- [ ] Non-staff user cannot view another user's SUPPORT thread (spot-check the list endpoint)
- [ ] Admin's reply to a SUPPORT thread appears to the originator in real-time via WS

### 2.6 Real-time infrastructure

- [x] Redis pub/sub bridges WS across gunicorn workers (verified per memory + PR-C4)
- [ ] WS reconnection — on disconnect, frontend reconnects with exponential backoff
- [ ] WS ticket issuance — short-lived (60s?), single-use (verified per CLAUDE.md Phase 3)
- [ ] Frontend handles WS messages arriving before the React state for the conversation is ready (race condition)

### 2.7 Attachments + file validation

- [ ] Allowed MIME types — image/*, PDF, text/plain, some office types? Verify whitelist
- [ ] Max file size enforced (should be ≤ 10 MB per env var `MAX_UPLOAD_SIZE_MB`)
- [ ] Path traversal filename protection — `test_chat_robustness::test_rejects_path_traversal_filename` covers this
- [ ] File served via `/uploads/...` or absolute URL? If absolute, is the URL validated as same-origin?

---

## Section 3 — Notifications — systematic review checklist

### 3.1 Event emission

20+ event types; check each one fires correctly on the triggering action:

| Event | Trigger | Expected destination |
|-------|---------|----------------------|
| `proposal_submitted` | Freelancer sends proposal on job | Client |
| `proposal_accepted` | Client accepts proposal | Freelancer |
| `contract_created` | Escrow funded on contract milestone | Both parties |
| `milestone_submitted` | Freelancer marks milestone delivered | Client |
| `milestone_approved` | Client approves milestone | Freelancer |
| `payment_received` | Escrow released | Freelancer |
| `review_received` | New review on user | Reviewed user |
| `new_message` | Any message (maybe gated?) | Other party in conversation |
| `service_approved` | Admin approves pending service | Freelancer |
| `service_rejected` | Admin rejects service | Freelancer (include reason) |
| `service_submitted` | Freelancer submits for review | All admins |
| `dispute_opened` | Dispute raised | Other party + admins |
| `dispute_resolved` | Admin closes dispute | Both parties |
| `buyer_request_offer_received` | Freelancer sends offer | Client |
| `buyer_request_offer_accepted` | Client accepts offer | Freelancer |
| `buyer_request_offer_rejected` | Client rejects offer | Freelancer |
| `order_requirements_submitted` | Client answers requirement questions | Freelancer |
| `order_delivered` | Freelancer marks delivery | Client |
| `order_auto_completed` | 3-day auto-complete fires | Freelancer |
| `seller_level_upgraded` | Daily recalc promotes seller | Freelancer |
| `chat_violation_warning` | First F6 violation | Violator |
| `system_alert` | Ad-hoc | Configurable |

Action: grep each event's emission site in backend code. Flag any that's missing (ever silently not firing).

### 3.2 In-app bell UI

- [ ] Bell badge count = unread notifications
- [ ] Poll interval (30s per README) — is this still right with WS push available?
- [ ] Clicking a notification marks it read and routes to the linked resource
- [ ] "Mark all as read" button exists and works

### 3.3 Email delivery

- [x] CID-embedded logo renders correctly in Gmail + Outlook (shipped 2026-04-23 per email branding work)
- [ ] Bilingual — emails pick the user's `locale` column, NOT the event emitter's locale
- [ ] Resend deliverability — SPF + DKIM + DMARC configured? Verify at https://resend.com dashboard
- [ ] Unsubscribe link at email footer → toggles `users.email_notifications_enabled` = false
- [ ] Per-type opt-out — some notification types (proposal / payment) are transactional and can't be disabled; others (tips, nudges) are optional

### 3.4 Background task correctness

- [ ] `notify_background()` uses a fresh DB session (fixes use-after-close per 2026-04-19 audit)
- [ ] Task failures are logged to Sentry but don't block the triggering action
- [ ] Tasks don't swallow critical errors silently

### 3.5 Locale + template rendering

- [ ] Templates for every event exist in both `_ar.html` and `_en.html`
- [ ] `{{ user_name }}` is properly escaped to prevent XSS in email bodies
- [ ] Arabic templates set `dir="rtl"` on root

---

## Section 4 — Priority ranking

Work top-down. Stop when time runs out; remaining items are backlog.

### P0 — Active bugs affecting users now

1. **"Failed to load messages" generic error** — fixed in current session (pending push)
2. **"Failed to load conversations" generic error** — fixed in current session (pending push)

### P1 — Gaps blocking a professional launch feel

1. **Pre-purchase client→freelancer DM** — blocked by antispam rule; needs rate-limited allow path
2. **No "New Conversation" UI** — users can only reply to existing threads. Messaging someone new requires navigating from their profile, which is non-obvious.
3. **Unread count accuracy** — verify badge never drifts from actual DB state. A common chat bug on long-running sessions.

### P2 — Polish

1. **Notification type coverage in bilingual emails** — spot-check any newly added NotificationType values from F1-F7 have email templates in both AR + EN
2. **Typing indicator reliability** — race condition on connection drop
3. **Presence stale-detection** — user closes tab without clean WS disconnect → presence says "online" forever

### P3 — Observability / future

1. Chat event analytics — how many messages/day, by conversation type
2. Notification delivery success rate (from Resend webhooks)

---

## Section 5 — How to execute

Because the audit is multi-day:

1. Each section's unchecked item = 10-30 minutes of investigation
2. Start with P0 → P1 → P2 → P3
3. Each finding becomes either a code PR or a "behaves as designed — document" entry in `decision-log.md`
4. When a section is 100% checked, mark the section heading complete + update go/no-go checklist

Running totals: check off above as we go so progress is visible without re-reading code.

---

## Current session (2026-04-24) progress

- ✅ Section 1 all 5 user-reported items triaged
- ⏳ Section 2.1-2.7 partial — several items already checked from prior review (marked `[x]`)
- ⏳ Section 3 partial — email branding complete, event emission coverage needs sweeping
- ⏳ Section 4 P0 items shipped as part of this audit's first commit

Next session: work through Section 2 end-to-end, then 3.1 event-emission coverage. Budget ~2-3 hours.
