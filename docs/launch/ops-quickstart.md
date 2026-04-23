# Kaasb Ops Quickstart

The one page you read during an incident. Detailed runbooks live elsewhere; link to them when you need depth.

Last updated: 2026-04-23. Maintainer: Mustafa Alrasheed.

---

## Access

```bash
# SSH to production
ssh -i ~/.ssh/id_ed25519 deploy@116.203.140.27 -p 2222

# Grafana (SSH tunnel — bound to 127.0.0.1:3001 on server, not exposed to internet)
ssh -L 3001:localhost:3001 -i ~/.ssh/id_ed25519 deploy@116.203.140.27 -p 2222 -N
# then open http://localhost:3001

# Admin panel (production web)
https://kaasb.com/admin   # requires superuser login
```

Server paths:

| What | Where |
|------|-------|
| Repo checkout | `/opt/kaasb` (managed by deploy workflow via `git reset --hard origin/main`) |
| Env file | `/opt/kaasb/.env.production` (chmod 600; contains all secrets) |
| Backups | `/opt/kaasb/backups/{db,files,configs}/` |
| Logs | `/var/log/kaasb/{backup,backup-monitor,retention,nginx-reload,vacuum}.log` |
| Node exporter textfile dir | `/var/lib/node_exporter/textfile/` |
| Cron file | `/etc/cron.d/kaasb` (6 entries; don't overwrite — append only) |

**Never push from the server.** The server is pull-only by design (`git reset --hard origin/main`). Push happens from the developer laptop.

---

## Deploy

Push to `main` → GitHub Actions runs CI → on success, auto-deploy fires. No manual action.

Manual control via `/opt/kaasb/deploy.sh` (preferred over direct `docker compose` — handles monitoring stack correctly):

```bash
./deploy.sh --pull       # Pull latest images + restart (fastest)
./deploy.sh --migrate    # Run Alembic migrations only
./deploy.sh --status     # Container health snapshot
./deploy.sh --logs       # Tail all service logs
./deploy.sh --rollback   # Revert to previous image tag (reads .release.previous)
./deploy.sh --backup     # One-off manual backup (same script cron runs nightly)
./deploy.sh full         # Full local build + migrate + restart
```

The GitHub Actions workflow (`.github/workflows/deploy.yml`) auto-includes both `docker-compose.prod.yml` and `docker-compose.monitoring.yml` since commit `09e63f0` — monitoring-stack changes now auto-apply on deploy.

Emergency manual deploy of a specific SHA:
- GitHub → Actions → "Kaasb Deploy to Production" → Run workflow → specify `image_tag=sha-xxxxxxx`

---

## Monitoring / observability

**Primary dashboard**: Grafana via SSH tunnel (see Access above). Provisioned dashboards auto-load from `docker/grafana/provisioning/`.

**Prometheus** (not exposed to the internet — query from inside):

```bash
# Get alertmanager/prometheus IPs
docker inspect kaasb_prometheus --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
docker inspect kaasb_alertmanager --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# Run an instant query
docker exec kaasb_prometheus promtool query instant http://localhost:9090 'up'

# Current alert rule states (inactive = metric OK, firing = alert on wire)
docker exec kaasb_prometheus wget -qO- http://localhost:9090/api/v1/rules | python3 -m json.tool
```

**Alertmanager**: 41 alert rules defined in [docker/prometheus/alert_rules.yml](../../docker/prometheus/alert_rules.yml), grouped by domain (application, auth, payments, database, redis, infrastructure, backups, ssl, websocket). All rules evaluated every 60s.

Alert routing (see [docker/alertmanager/alertmanager.yml](../../docker/alertmanager/alertmanager.yml)):

| Severity | Route | Batch window |
|----------|-------|--------------|
| `critical` | Discord webhook (fastest) | 0s group_wait, 1m group_interval, 30m repeat |
| `high` | Discord webhook | 30s group_wait, 5m group_interval, 30m repeat |
| `medium` | Email only | 5m group_wait, 30m group_interval, 12h repeat |
| `low` | Email only | 24h repeat |

Phase 2.6 smoke test (proven 2026-04-23): both Discord + email paths including auto-resolve notifications.

**Sentry**: backend exceptions. DSN in `.env.production`. Front-end has no Sentry yet (Phase 3+).

---

## Backups

Scheduled: daily 02:00 UTC via `/etc/cron.d/kaasb`. Three stages:

1. DB dump (pg_dump → gzip)
2. User uploads tar.gz (`kaasb_backend_uploads` volume)
3. Configs tar.gz (`.env.production`, nginx.conf, alertmanager.yml, SSL certs)

Each stage writes a SHA-256 checksum sidecar.

Retention: 7 daily, 4 weekly (Sunday), 12 monthly (1st). S3-compatible off-site upload supported via `S3_BUCKET` env var (not yet configured as of 2026-04-23 — Phase 2.5 follow-up).

**Prometheus alerts fire if backups stop.** `kaasb_last_backup_timestamp_seconds` is written by `backup.sh` to the node_exporter textfile collector; `BackupTooOld` alert triggers if >26h (warn) or >48h (critical).

Manual backup:

```bash
sudo bash /opt/kaasb/scripts/backup.sh
```

Monthly restore verification:

```bash
# The scheduled cron (1st of each month, 04:00 UTC) runs this:
sudo bash /opt/kaasb/scripts/backup-verify.sh
```

DR procedure: [docs/disaster-recovery.md](../disaster-recovery.md). RTO ≤4h, RPO ≤24h.

**Known Phase-2 incident (2026-04-07 → 2026-04-23):** `backup.sh` had a `set -e`/`pipefail` bug that killed the script after the DB stage. Only DB was backed up for 16 days; files + configs directories were empty. Fixed in commits `b03ac55` + `310d22e`. Decision log entry: [docs/launch/decision-log.md](decision-log.md).

---

## Secrets rotation

Rotate quarterly (Phase 12 calendar). All live in `/opt/kaasb/.env.production` (chmod 600).

| Secret | When to rotate | How |
|--------|----------------|-----|
| `SECRET_KEY` | Quarterly OR on compromise | `openssl rand -hex 32`; **invalidates all sessions immediately** |
| `GRAFANA_ADMIN_PASSWORD` | Quarterly | Any strong pw; then `docker compose ... up -d grafana` |
| `DB_PASSWORD` | Quarterly | `openssl rand -base64 24 \| tr -dc 'a-zA-Z0-9' \| head -c 32`; restart db + backend |
| `REDIS_PASSWORD` | Quarterly | `openssl rand -hex 24`; restart redis + backend |
| `QI_CARD_API_KEY` | Every 6 months OR on incident | Via QiCard merchant portal |
| `RESEND_API_KEY` | Yearly | Via Resend dashboard |
| `HEALTH_BEARER_TOKEN` | Quarterly | `openssl rand -hex 20` |
| GitHub Actions secrets | On person leaving team | repo Settings → Secrets and variables → Actions |

QiCard merchant portal creds: stored in password manager per [project_admin_team_and_merchant_portal.md](../../../.claude/projects/c--Users-Mustafa-Alrasheed-Desktop-kaasb/memory/project_admin_team_and_merchant_portal.md) memory. Never in repo or env file.

---

## Cert renewal

Handled by the `kaasb_certbot` container (infinite loop: `certbot renew --webroot --quiet` every 12h). No host cron needed for the renew itself.

Nginx reload to pick up renewed cert: daily 03:15 UTC cron (added 2026-04-23). Cert expires 2026-06-27 — first real renewal ~2026-05-28.

Verify:

```bash
# When does the current cert expire?
openssl x509 -noout -enddate -in /var/lib/docker/volumes/kaasb_letsencrypt/_data/live/kaasb.com/fullchain.pem 2>/dev/null || \
  docker run --rm -v kaasb_letsencrypt:/etc/letsencrypt alpine:3.19 sh -c 'apk add -q openssl; openssl x509 -noout -enddate -in /etc/letsencrypt/live/kaasb.com/fullchain.pem'

# Dry-run a renewal (does not write cert)
docker exec kaasb_certbot certbot renew --dry-run
```

Prometheus `SSLCertExpiringSoon` alert fires 14 days before expiry (high severity → Discord); `SSLCertExpiringCritical` fires 3 days before (critical severity → Discord).

---

## Incident: symptom → first action

| Symptom | First thing to check |
|---------|----------------------|
| Platform down (https://kaasb.com returns 5xx or times out) | `./deploy.sh --status` → which container is unhealthy; `docker logs <container> --tail 200` |
| Discord alert: HighErrorRate | Sentry → most recent exception cluster; correlate with backend logs `docker logs kaasb_backend --tail 200` |
| Discord alert: PostgresDown | `docker compose -f docker-compose.prod.yml --env-file .env.production ps db`; if stopped: `up -d db`; if unhealthy: check `docker logs kaasb_db` for disk/OOM |
| Discord alert: BackupTooOld | `sudo tail -30 /var/log/kaasb/backup.log`; if stuck: `sudo bash /opt/kaasb/scripts/backup.sh 2>&1 \| tail -20` |
| Email alert: DiskSpaceWarning (>80%) | `df -h`; prune `/opt/kaasb/backups/db` daily files, verify retention cron ran |
| SSL expiring alert | `docker exec kaasb_certbot certbot renew --dry-run` — if passes, wait for scheduled renewal; if fails, investigate ACME challenge |
| User reports payment not going through | `docker logs kaasb_backend --tail 500 \| grep -i "qi_card"`; check QiCard merchant portal for transaction state |
| Support ticket storm | `/admin` panel → Disputes tab, Support tab; triage per [support runbook](../admin/support-runbook.md) (to be written in Phase 3) |

If in doubt: **roll back to the previous tag**:

```bash
cd /opt/kaasb && ./deploy.sh --rollback
```

---

## Who gets paged for what

Alert severity | Page via | Acknowledge by
---|---|---
critical | Discord (instant) | Replying in the alert thread with "ack"
high | Discord (30s batch) | Same as critical
medium | Email (5m batch, 12h repeat) | Resolving underlying issue
low | Email (24h repeat) | Weekly ops review

With 3 admins (Mustafa, Rasheed, `admin@kaasb.com`) and no formal on-call rotation yet — whoever sees it first replies "taking" and owns the incident until resolution. Formal rotation doc in Phase 12.

---

## Doc links for deeper dives

- [Deployment guide](../deployment-guide.md) — bootstrap a fresh server
- [Disaster recovery](../disaster-recovery.md) — RTO/RPO, restore procedures
- [DR runbooks](../dr/runbooks.md) — per-failure scenario playbooks
- [Business continuity](../dr/business-continuity.md) — comms + escalation
- [RTO/RPO matrix](../dr/rto-rpo-matrix.md) — recovery targets by failure type
- [Maintenance guide](../maintenance-guide.md) — routine operations
- [API reference](../api-reference.md) — backend API surface
- [Decision log](decision-log.md) — why things are the way they are
- [Go/no-go checklist](go-no-go-checklist.md) — what to verify before flipping public

---

## Last resort

If you're on this page during a critical incident and nothing in it resolves the issue, the escalation path is:

1. **Roll back** (`./deploy.sh --rollback`) to return to a known-good state
2. **Pause traffic** if needed — `docker compose -f docker-compose.prod.yml --env-file .env.production stop nginx` takes the site offline cleanly; restart with `up -d nginx`
3. **Open an issue** at https://github.com/mustafaalrasheed/kaasb/issues with `[INCIDENT]` in the title
4. **Pull in** Rasheed (`rasheed.ghassan88@gmail.com`) as second pair of eyes

Site offline is bad. Site serving corrupt data is worse. Always prefer to pause over to guess.
