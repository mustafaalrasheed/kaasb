# Phase 4 — QiCard v0 → v1 3DS Migration

Opened 2026-04-25. **Production payments are currently broken**: the v0 host
`api.pay.qi.iq` returns NXDOMAIN, so every fund-escrow attempt 502s out
through `qi_card_client.create_payment`. v1 3DS at `3ds-api.qi.iq` is the
only live endpoint — Phase 4 is the migration.

This doc is the rollout plan, the credentials request email, and the
verification checklist for whoever ships the migration.

---

## Where the work is blocked

- **No QiCard v1 credentials in hand.** We need a Basic-auth user/pass +
  X-Terminal-Id from QiCard's merchant onboarding team. UAT creds first
  for smoke testing, then production after that's green.
- **No v1 OpenAPI body schemas confirmed by us.** The endpoint set is
  known (4 endpoints — see `memory/project_qicard_api_surface.md`) but
  we have not seen the exact request/response JSON shapes. Best to read
  these straight from the spec at provisioning time rather than guess.

Until the credentials and spec arrive, the client is shipped behind the
`QI_CARD_USE_V1=false` flag and continues to use v0. Production stays
broken until cutover; the only short-term fix for live payments is to
flip the flag on with valid creds.

---

## Email to send to QiCard

Send this to your QiCard merchant onboarding contact (the one who provisioned the v0 API key). If you don't have one, the onboarding mailbox is usually `merchant@qi.iq` or via the QiCard merchant portal contact form.

> **Subject:** Kaasb (kaasb.com) — request for v1 3DS API credentials + integration docs
>
> Hello,
>
> I'm reaching out to migrate Kaasb from the QiCard v0 redirect API (`api.pay.qi.iq`) to the v1 3DS API. We've confirmed the v0 host is no longer resolving, and we'd like to cut over as soon as possible so our customers can resume paying for orders.
>
> To complete the migration we need:
>
> 1. **UAT credentials for v1 3DS:**
>    - Basic auth username + password
>    - `X-Terminal-Id` value
>    - UAT host confirmed (we have `https://uat-sandbox-3ds-api.qi.iq` on file — please confirm or correct)
> 2. **Production credentials for v1 3DS:**
>    - Same three items as above, for production
>    - Production host confirmed (we have `https://3ds-api.qi.iq` on file)
> 3. **Integration documentation:**
>    - Full OpenAPI / Swagger spec for the v1 3DS API (we'd like the exact request and response body schemas for the four endpoints: `POST /api/v1/payment`, `GET /api/v1/payment/{paymentId}/status`, `POST /api/v1/payment/{paymentId}/cancel`, `POST /api/v1/payment/{paymentId}/refund`)
>    - Sandbox test card numbers + 3DS challenge instructions
>    - Any signature / RSA-key requirements (we plan to use Basic auth + `X-Terminal-Id`; please confirm RSA `X-Signature` is optional rather than required)
>    - Allowed IPs for callbacks (if any) so we can whitelist our backend (Hetzner CPX22 — we can provide our outbound IPs once we know what range you need)
> 4. **Cutover guidance:**
>    - Whether our existing merchant account needs to be re-provisioned for v1 3DS, or if the existing `apiKey` migrates automatically
>    - Whether there's a recommended grace period running v0 + v1 in parallel, or if v0 will simply be turned off
>    - Whether v0 transactions in flight at the cutover moment will continue to settle, or whether we need to drain them first
>
> Our merchant code / contact on file is **\[your QiCard merchant ID]** registered under **\[your business name]**. Best email for us is `support@kaasb.com` and direct contact is `\[your name + phone]`.
>
> Happy to jump on a call if a walk-through is faster than email.
>
> Thanks,
> \[your name]
> Kaasb (https://kaasb.com)

Fill in the `[brackets]` before sending. If they ask for fixed outbound IPs, the production server is at `116.203.140.27`.

---

## Code changes already in place (commit 0e1be45 onward)

- **`backend/app/core/config.py`** has the v1 setting slots:
  - `QI_CARD_V1_HOST` (default `https://3ds-api.qi.iq`)
  - `QI_CARD_V1_SANDBOX_HOST` (default `https://uat-sandbox-3ds-api.qi.iq`)
  - `QI_CARD_V1_USER`, `QI_CARD_V1_PASS`, `QI_CARD_V1_TERMINAL_ID` (empty)
  - `QI_CARD_USE_V1` (false; feature flag)
- Production-mode validator enforces all four credential slots are populated when `QI_CARD_USE_V1=true`, so a half-configured boot fails fast instead of silently 500ing customer requests.

The `qi_card_client.py` v1 implementation lands in a follow-up commit, after we have confirmed body schemas. See "Implementation steps" below.

---

## Implementation steps (after creds + spec arrive)

1. **Verify creds against UAT.** Run a curl smoke test:
   ```bash
   curl -u "$QI_CARD_V1_USER:$QI_CARD_V1_PASS" \
        -H "X-Terminal-Id: $QI_CARD_V1_TERMINAL_ID" \
        -H "Content-Type: application/json" \
        -X POST "$QI_CARD_V1_SANDBOX_HOST/api/v1/payment" \
        -d "<minimum valid body from the spec>"
   ```
   Stop here if this doesn't succeed — there's no point writing code against an API you can't call.
2. **Add `qi_card_payment_id` persistence at create-time.** Right now the v0 client uses `external_transaction_id = order_id` because v0 has no separate payment ID. v1 returns its own `paymentId` in the create response — store that on `Transaction.external_transaction_id` (the column already exists).
3. **Implement `QiCardClientV1.create_payment` / `verify_payment` / `cancel_payment` / `refund_payment`.** Same async + circuit-breaker + idempotency-cache scaffolding as the v0 client. Add a single `QiCardClient.factory()` that returns v0 or v1 based on `settings.QI_CARD_USE_V1`.
4. **Wire `payment_service.fund_escrow` to use the new factory.** No call-site changes — same `create_payment(amount_iqd, order_id, …)` signature. Internally route through v1 when the flag is set.
5. **Wire `payment_service.refund_escrow` to call `refund_payment` for real** (currently unused — the catch in dispute resolution falls through to manual). Hook into `dispute_service.resolve_with_refund` so that when the admin clicks "Refund" on a dispute, the v1 refund fires automatically. Keep the manual fallback path for cases where the v1 refund returns an error code we can't resolve.
6. **Smoke test on UAT end-to-end.** Use the documented sandbox test card to fund an escrow; verify the redirect, the success-callback, the resulting `Escrow.status=FUNDED`, then trigger a refund through the dispute flow and verify status goes to `REFUNDED` + the v1 status endpoint reports `REFUNDED`.
7. **Stage on production with the flag off.** Set the four `QI_CARD_V1_*` env vars in production but leave `QI_CARD_USE_V1=false`. Boot the app — it should start cleanly because the validator only fires when the flag is on.
8. **Flip the flag on production.** `QI_CARD_USE_V1=true` + `./deploy.sh --pull`. Watch Sentry + the Grafana payments dashboard for 10 minutes.
9. **Send one real low-value test payment** through the live site (e.g. fund a 1,000 IQD escrow on a test service of your own). Verify it lands in the QiCard merchant app.
10. **Update Known Issue #2 in `CLAUDE.md`** to "RESOLVED" and remove the manual-only banner from `docs/admin/refund-runbook.md`.

---

## Rollback plan

If anything misbehaves after the flag flip:

1. `QI_CARD_USE_V1=false` in `.env.production`
2. `./deploy.sh --pull`
3. The v0 client takes over again. (It's still broken because v0 host is dead, but at least the v1 errors stop. The actual recovery path is to fix whatever the v1 mismatch was, not to roll back.)

In other words, treat this as forward-only — there's no working v0 to fall back to. The pragmatic safe-deploy is "land the v1 code disabled, smoke-test on UAT, schedule the flag-flip during low-traffic hours."

---

## Verification checklist (before declaring Phase 4 done)

- [ ] UAT: create payment → redirect → success callback → escrow FUNDED.
- [ ] UAT: create payment → redirect → cancel → escrow stays PENDING.
- [ ] UAT: create payment → fund → refund via dispute → escrow REFUNDED.
- [ ] UAT: create payment → status endpoint → returns expected stage (`PENDING` / `COMPLETED` / `REFUNDED` / `CANCELLED`).
- [ ] Production: one real low-value end-to-end payment confirmed in the QiCard merchant app.
- [ ] Production: Sentry quiet for 30 minutes after flag flip.
- [ ] CLAUDE.md Known Issue #2 marked resolved + Progress Tracker updated.

---

## Why we didn't ship the client code in this session

Without UAT credentials we'd be guessing the request/response body schemas from the endpoint paths alone. Guessed schemas catch nothing in CI (no real API to call) and surface bugs only when a real customer tries to pay — exactly the failure mode this migration is trying to fix. Shipping the config slots + the validator + this rollout plan makes the next session's work mechanical: drop in creds, run the curl, write the client against the confirmed shape.
