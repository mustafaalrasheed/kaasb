# Kaasb Launch Decision Log

One row per non-obvious decision taken during the beta → launch work. This exists so future-you (or any admin/engineer who joins later) can answer "why did we choose X?" without archaeology.

Add new rows at the top. Keep each entry short: what was decided, why, who decided, when.

---

## 2026-04-24 — Crosscutting quality bars applied to every phase (user reminder)

**Decision:** Four concerns thread through every remaining phase as non-negotiable quality bars, not separate phases:

1. **Security** — current posture is strong (rate limiting, CSRF, HSTS, CSP, Sentry PII scrubbing, JWT rotation, dual-control payouts, HMAC-signed QiCard redirects, pip-audit in CI, GitGuardian scanning). **Each phase must not degrade it.** New dependencies need pip-audit/npm-audit clean. New endpoints need auth + rate-limiting + input validation. Secrets stay in `.env.production` only — never in repo, never in logs (scrubber config in `backend/app/main.py:_SENTRY_SCRUB_KEYS`). Quarterly rotation in Phase 12.

2. **SEO** — per-page `generateMetadata`, Organization + Website JSON-LD, sitemap.ts, robots.ts already in place. Gaps closed in Phase 7 (`/services/[slug]` metadata + Service JSON-LD, `/help`+`/faq`+`/how-it-works` pages). Every new public page must ship with: meta title + description, OG image, canonical URL, appropriate JSON-LD schema, sitemap entry.

3. **UI/UX** — AR-primary RTL is the default; every new feature verified on RTL on mobile before shipping. Fiverr-parity gaps (switch-to-selling toggle, rich seller onboarding, custom offers in chat) land in Phase 7. Dashboard empty states need "what to do next" cards — no blank slates. Any destructive action requires explicit confirmation dialog. Every form has client + server validation with error messages in the active locale.

4. **Professionalism** — legal pages reviewed by Iraqi counsel (Phase 10 blocker, running as parallel Legal Track A). Admin audit log + dual-control payouts shipped 2026-04-20. Every admin action must write a row to `admin_audit_logs`. Error pages (`404`, `500`, `503`) must be bilingual and on-brand, not Next.js defaults. No English leaking into the Arabic UI. Consistent typography + spacing from shadcn/ui design tokens. Never ship partially-migrated features to users — use feature flags or gate behind admin role.

**How to apply:** Before marking any Phase complete, check that phase's work against these four bars. Flag any regression explicitly in the phase's commit or its decision-log entry. The go/no-go checklist already enforces some of this at the Phase 10 gate; the bars above apply continuously, not just at the gate.

---

## 2026-04-23 — Phase 3 runbooks shipped with placeholders pending QiCard portal walkthrough

**Decision:** Ship `payout-runbook.md` and `refund-runbook.md` with clearly-marked `[PENDING QICARD PORTAL WALKTHROUGH]` sections rather than wait for the walkthrough before publishing anything.

**Why:** Three of the four Phase 3 runbooks (dispute, support, payout-Kaasb-side, refund-Kaasb-side) are fully actionable right now. Waiting to publish them until the portal walkthrough is done would block Phase 3 close-out on an external dependency (user availability). The placeholder approach lets admins act on 80% of real cases immediately — only the manual QiCard portal click-path is stubbed, and during that window admins can fall back to calling QiCard merchant support (`qicard@qi.iq` / `+964 771 640 4444`) for portal help.

**How to apply:**

1. On 2026-04-24 (or later, whenever user returns), do the walkthrough — see `project_pending_qicard_walkthrough.md` in memory for the exact question list.
2. Fill in the placeholder blocks in both runbook files.
3. Remove the ⚠️ status banner from the top of each file.
4. Commit as `docs(ops): fill QiCard portal sections in payout + refund runbooks`.
5. Delete `project_pending_qicard_walkthrough.md` memory + its index line.

**Go/no-go impact:** The checklist line "Each admin has logged into Kaasb admin panel + QiCard merchant portal successfully" cannot be checked until the walkthrough is done and the runbooks are complete. This is therefore a Phase 10 (soft public launch) blocker. Not blocking intermediate phases (4-9).

---

## 2026-04-23 — Don't wire monitor-backups.sh's own alert channels

**Decision:** Leave `ALERT_WEBHOOK`, `ALERT_EMAIL`, and related vars used by `scripts/monitor-backups.sh` unset in `.env.production`. Primary alerting path (Prometheus `BackupTooOld` rule → Alertmanager → Discord) covers backup staleness; setting the secondary path would duplicate every backup alert.

**Why:** The monitor-backups script predates the `BackupTooOld` Prometheus rule and was designed to be a standalone safety net with its own webhooks. Now that `kaasb_last_backup_timestamp_seconds` is wired into Prometheus (commits `af39716` + `b03ac55` + `310d22e`) and Alertmanager routing was proven end-to-end in Phase 2.6, the primary path is authoritative. The secondary checks monitor-backups does that Prometheus doesn't (checksum drift, per-file size) land in `/var/log/kaasb/backup-monitor.log` and get eyes-on during the weekly ops review.

**How to apply:** If a future silent backup failure slips past the Prometheus path (e.g., a script bug that writes a fresh `.prom` file but fails the actual backup), wire `ALERT_WEBHOOK=$ALERTMANAGER_DISCORD_WEBHOOK_URL` in `.env.production` to reinstate the secondary. Two-line change; no script edit required.

---

## 2026-04-23 — **DR gap discovered**: files + configs backups silently failed for 2+ weeks

**Decision:** Recorded here because it's the single most material finding of Phase 2 and the go/no-go checklist needs to reflect it.

**What happened:** `scripts/backup.sh` had a latent `set -euo pipefail` interaction with `zcat | head -1`. zcat's SIGPIPE (exit 141) killed the script silently right after the DB dump. For **16+ days (2026-04-07 → 2026-04-23)** only the first of three backup stages actually ran:

- ✅ Database dumps written nightly (`/opt/kaasb/backups/db/`)
- ❌ User upload files **never backed up** (empty `/opt/kaasb/backups/files/`)
- ❌ Configs, `.env.production`, `nginx.conf`, SSL certs **never backed up** (empty `/opt/kaasb/backups/configs/`)

Monitor-backups.sh did not alert because `ALERT_WEBHOOK` / `ALERT_EMAIL` are not configured in `.env.production`. The `BackupTooOld` Prometheus alert couldn't fire either — no metric was being written.

**Why it matters:** If the backend uploads Docker volume had been corrupted (user avatars, service images, message attachments) or `.env.production` had been deleted, there would have been **no recovery path**. Beta traffic is low so data loss exposure is small, but the same bug at GA traffic levels would be a disaster.

**Fix:** One-line change in `backup.sh`: `HEADER_LINE=$(zcat ... | head -1 || true)` (matches the `|| true` pattern already used by the adjacent `TABLE_COUNT` line). Root cause was inconsistency, not deep design.

**Follow-ups added to the go/no-go checklist:**

1. Verify a full 3-stage backup (DB + files + configs) completes successfully.
2. Confirm the `.prom` metric file gets written so `BackupTooOld` has a signal source.
3. Wire `ALERT_EMAIL` and/or `ALERT_WEBHOOK` in `.env.production` so `monitor-backups.sh` actually speaks up next time something silently breaks.
4. Consider adding `bash -x` tracing or explicit `log "Stage N complete"` between stages so any future silent failure shows up in the log.

**How to apply:** Any new ops script added to `scripts/` that uses `set -e` + pipelines must either consistently `|| true` any subshell capture, or use `awk`/`sed` patterns that read to EOF instead of `head`-style early-exit readers. PR review should flag this.

---

## 2026-04-23 — Phase 2 ops findings: cron mostly pre-installed, certbot auto-renews via container, textfile collector for backup metric

**Decisions:**

1. `/etc/cron.d/kaasb` on prod already has 5 of the 6 entries the plan called for — daily backup 02:00, backup monitor every 30min, **monthly live-restore verification 1st @ 04:00** (bonus — a `scripts/backup-verify.sh` exists and is scheduled), daily GDPR retention 03:00, weekly VACUUM ANALYZE Sunday 03:30. Phase 2 only needed to append **one** new line: daily nginx reload at 03:15 to pick up certbot-renewed certs.

2. Certbot renewal is not a host cron. It runs inside the `kaasb_certbot` container via [docker-compose.prod.yml:237](../../docker-compose.prod.yml#L237): `while :; do certbot renew --webroot ... --quiet; sleep 12h; done`. No host cron is required; the container handles the ~12h polling. `--quiet` + cert not yet close to expiry (issued 2026-03-29, expires 2026-06-27) means `docker logs kaasb_certbot` is empty and will stay that way until ~2026-05-28. The new 03:15 nginx-reload cron ensures renewed certs become active without a manual restart.

3. For the `kaasb_last_backup_timestamp_seconds` Prometheus metric we chose **node_exporter textfile collector** over pushgateway. Pushgateway would require a new container + config + secret. Textfile collector is two lines of diff: a flag + a volume mount in [docker-compose.monitoring.yml](../../docker-compose.monitoring.yml), and `backup.sh` writes `/var/lib/node_exporter/textfile/kaasb_backup.prom` atomically (`mktemp` + `mv`) on successful completion. Host dir `/var/lib/node_exporter/textfile` was created pre-deploy.

**Why:** Simplest path that activates the `BackupTooOld` alert rule (already in `alert_rules.yml`) with the least new infrastructure.

**How to apply:** If we ever need multiple scripts to emit custom metrics (e.g. backup-verify.sh, GDPR retention stats), all of them write `.prom` files into the same dir. Any script writing there must use atomic mv (not `>` redirect) so node_exporter never scrapes a half-written file.

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

```markdown
## YYYY-MM-DD — Short title

**Decision:** What you decided in one sentence.

**Why:** The reason. Include the constraint or data that drove it.

**Action:** What flows from this. Where to track it.
```
