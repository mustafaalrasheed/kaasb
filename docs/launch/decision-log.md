# Kaasb Launch Decision Log

One row per non-obvious decision taken during the beta → launch work. This exists so future-you (or any admin/engineer who joins later) can answer "why did we choose X?" without archaeology.

Add new rows at the top. Keep each entry short: what was decided, why, who decided, when.

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
