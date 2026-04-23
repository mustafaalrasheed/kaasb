# Kaasb Soft Public Launch Go / No-Go Checklist

Every line below must be **green** before flipping Phase 10 (soft public launch). One non-green line = no-go, no exceptions. Fill in checkboxes as you validate.

Maintainer: Mustafa Alrasheed. Last revised: 2026-04-23.

---

## Technical

- [ ] Backend CI green on `main` for 7 consecutive days (ruff + mypy + alembic check + pytest)
- [ ] Frontend CI green on `main` for 7 consecutive days (eslint + tsc + build + 6 Playwright smoke tests)
- [ ] Backend integration test suite (Phase 5) green on `main` for 7 consecutive days
- [ ] QiCard v1 refund path exercised successfully against ≥1 UAT payment + ≥1 real dispute
- [ ] Full end-to-end closed-beta order observed: fund → deliver → release → QiCard payout confirmed
- [ ] All migrations applied: `alembic check` on prod DB reports "No new upgrade operations detected"
- [ ] No open P0 Sentry issue
- [ ] Rate limits verified under load (sustained 10 rps on `/auth/login`, `/services/search`)

## Ops

- [ ] Backup cron installed in `/etc/cron.d/kaasb`; last successful backup < 26h old per Grafana
- [ ] Off-site backup copy verified present (S3 or equivalent) if configured
- [ ] Manual DR restore executed successfully within the last 30 days
- [ ] Certbot renewal cron installed; `certbot renew --dry-run` passes
- [ ] Grafana admin password rotated off default; SSH tunnel access documented
- [ ] Alertmanager test alert verified: Discord + email both received within 3 min of trigger
- [ ] `/health/detailed` returns healthy with `HEALTH_BEARER_TOKEN` set
- [ ] Prometheus `up` metric green for all scrapers

## Product & content

- [ ] `/` (home) loads cleanly in AR and EN on mobile + desktop
- [ ] `/services/[slug]` has real `generateMetadata()` and JSON-LD Service schema
- [ ] `/help`, `/how-it-works`, `/faq` shipped, bilingual, linked from footer
- [ ] `/privacy` and `/terms` no longer display the "pending formal review" banner
- [ ] Legal pages have real registered entity info (no `__REG_NO__` / `__ADDRESS__` placeholders)
- [ ] ≥8 real freelancer profiles live with avatar + bio + ≥1 service
- [ ] ≥5 real job listings posted from clients
- [ ] Seed categories present and visible on `/services` filter

## Analytics

- [ ] Plausible (or chosen analytics) showing live pageviews from production
- [ ] 6 custom events firing: `signup_started`, `signup_completed`, `job_posted`, `service_order_funded`, `order_completed`, `dispute_opened`
- [ ] Grafana "Kaasb Business KPIs" dashboard reachable, populated
- [ ] 3 error budgets documented and observed for ≥7 days

## Customer support

- [ ] `support@kaasb.com` delivers to all 3 admins; test email acknowledged within 1 business hour
- [ ] 8 bilingual support macros committed to `docs/admin/support-macros.md`
- [ ] `/help` page publishes SLA (first response ≤ 8 business hours, resolution ≤ 48 hours)
- [ ] In-app "Contact Support" modal on `/dashboard/messages` verified working end-to-end
- [ ] One full test support thread resolved in production before Go

## Admin operations

- [ ] `docs/admin/payout-runbook.md` committed and read by all 3 admins
- [ ] `docs/admin/refund-runbook.md` committed and read by all 3 admins
- [ ] `docs/admin/dispute-runbook.md` committed and read by all 3 admins
- [ ] `docs/admin/support-runbook.md` committed and read by all 3 admins
- [ ] QiCard merchant portal credentials stored in shared password manager (NOT in repo or `.env`)
- [ ] Each admin has logged into Kaasb admin panel + QiCard merchant portal successfully

## Legal

- [ ] Iraqi counsel engaged with a signed scope of work
- [ ] Terms of Service reviewed and redlined by counsel; redlines merged
- [ ] Privacy Policy reviewed and redlined by counsel; redlines merged
- [ ] Counsel sign-off letter filed at `docs/launch/legal-signoff-YYYY-MM-DD.pdf`
- [ ] QiCard merchant-agreement summary received from QiCard confirming fund-holding terms
- [ ] Kaasb legal entity registered (commercial registration number available)

## Business

- [ ] Marketing announcement drafted for LinkedIn (AR + EN)
- [ ] `kaasb.com/blog/launch` page drafted and ready to publish
- [ ] Startup-directory submissions pre-filled (MENAbytes, Wamda, ≥2 others)
- [ ] Founder's Facebook / LinkedIn / Twitter/X scheduled announcement queued
- [ ] Founder is physically/mentally available for a 48-hour watch window post-flip

---

## Sign-off

When every box above is checked, fill in and commit:

- Date flipped public: _______________
- Flipped by: _______________
- Beta-v1 tag: `beta-v1`  (Phase 1 snapshot — compare via `git diff beta-v1 HEAD` to see everything shipped between beta and launch)
