# Kaasb Platform — Disaster Recovery Runbooks

**Last updated:** 2026-03-27
**Applies to:** Production stack on Hetzner CPX22 (116.203.140.27)
**Owner:** Platform Engineering

---

## Quick Reference

| Scenario | Severity | RTO | Go to |
|----------|----------|-----|-------|
| [1. Complete Server Failure](#scenario-1-complete-server-failure) | Critical | 3–5 h | §1 |
| [2. Database Corruption or Data Loss](#scenario-2-database-corruption-or-data-loss) | Critical | 2–4 h | §2 |
| [3. Accidental File Deletion](#scenario-3-accidental-file-deletion) | High | 30–60 min | §3 |
| [4. Failed Database Migration](#scenario-4-failed-database-migration) | High | 15–60 min | §4 |
| [5. Security Incident / Compromise](#scenario-5-security-incident--compromise) | Critical | 4–8 h | §5 |
| [6. Disk Full / Resource Exhaustion](#scenario-6-disk-full--resource-exhaustion) | Medium | 15–30 min | §6 |

---

## Prerequisites

Before any recovery, verify you have:
- [ ] SSH access to the production server (or Hetzner console access)
- [ ] `.env.production` credentials stored in your team password manager
- [ ] At least one verified backup (run `bash /opt/kaasb/scripts/backup-verify.sh` to check)
- [ ] The [RTO/RPO Matrix](rto-rpo-matrix.md) open for reference

---

## Scenario 1: Complete Server Failure

**Trigger:** Server is unreachable, Hetzner shows hardware failure, or server is destroyed.

**RPO:** Up to 24 hours (last successful backup)
**RTO:** 3–5 hours

### Step 1 — Provision a new server

```bash
# In Hetzner Cloud Console (console.hetzner.cloud):
# 1. Create new CPX22 (or larger) — Ubuntu 24.04
# 2. Add your SSH public key
# 3. Note the new server IP

NEW_IP="x.x.x.x"  # Set this
```

### Step 2 — Bootstrap the new server

```bash
ssh root@${NEW_IP}

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# Create app directory
mkdir -p /opt/kaasb/backups/{db,files,configs}
mkdir -p /var/log/kaasb
```

### Step 3 — Restore codebase

```bash
# Clone the repo (uses git — no secrets in repo)
git clone https://github.com/mustafaalrasheed/kaasb /opt/kaasb
cd /opt/kaasb
```

### Step 4 — Restore configuration

```bash
# Option A: from S3 backup (if S3_BUCKET was configured)
aws s3 cp s3://kaasb-backups/daily/configs/kaasb-configs-daily-LATEST.tar.gz \
    /opt/kaasb/backups/configs/

# Option B: from local backup (if you have the file)
scp kaasb-configs-daily-LATEST.tar.gz root@${NEW_IP}:/opt/kaasb/backups/configs/

# Restore configs (includes .env.production, nginx.conf, SSL certs)
bash /opt/kaasb/scripts/restore.sh \
    --config /opt/kaasb/backups/configs/kaasb-configs-daily-LATEST.tar.gz \
    --dry-run    # Preview first

bash /opt/kaasb/scripts/restore.sh \
    --config /opt/kaasb/backups/configs/kaasb-configs-daily-LATEST.tar.gz
```

### Step 5 — Restore database

```bash
# Copy DB backup to new server
scp kaasb-db-daily-LATEST.sql.gz root@${NEW_IP}:/opt/kaasb/backups/db/

# Start DB container first
cd /opt/kaasb
docker compose -f docker-compose.prod.yml --env-file .env.production up -d db
sleep 15  # Wait for Postgres to initialise

# Restore (includes migrations, service restart)
bash /opt/kaasb/scripts/restore.sh \
    --db /opt/kaasb/backups/db/kaasb-db-daily-LATEST.sql.gz
```

### Step 6 — Restore user-uploaded files

```bash
# Copy files backup
scp kaasb-files-daily-LATEST.tar.gz root@${NEW_IP}:/opt/kaasb/backups/files/

bash /opt/kaasb/scripts/restore.sh \
    --files /opt/kaasb/backups/files/kaasb-files-daily-LATEST.tar.gz
```

### Step 7 — Start all services

```bash
cd /opt/kaasb
./deploy.sh full
```

### Step 8 — Verify health

```bash
curl http://${NEW_IP}/api/v1/health
curl http://${NEW_IP}/api/v1/health/ready
./deploy.sh --status
```

### Step 9 — Update DNS

In your DNS provider (Hetzner / Fastcomet):
- Update `A` record for `kaasb.com` → `${NEW_IP}`
- Update `A` record for `www.kaasb.com` → `${NEW_IP}`
- TTL propagation: 15 min to 24 hours

### Step 10 — Re-issue SSL certificate

Once DNS propagates:
```bash
./deploy.sh --ssl
```

### Step 11 — Communicate

See [Business Continuity Plan](business-continuity.md) §3 for communication templates.

---

## Scenario 2: Database Corruption or Data Loss

**Trigger:** `psql` errors, missing tables, wrong row counts, application 500 errors on data access.

**RPO:** Up to 24 hours (last backup), minutes if WAL archiving is enabled
**RTO:** 2–4 hours

### Step 1 — Assess damage

```bash
ssh root@116.203.140.27
cd /opt/kaasb

# Can you connect?
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec db psql -U "${DB_USER}" -d "${DB_NAME}" -c "\dt"

# Check error logs
docker compose -f docker-compose.prod.yml --env-file .env.production \
    logs db --tail=100

# Row count check (compare to expected baseline)
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec db psql -U "${DB_USER}" -d "${DB_NAME}" -c \
    "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"
```

### Step 2 — Put application in maintenance mode

```bash
# Stop API and frontend, leave DB running
docker compose -f docker-compose.prod.yml --env-file .env.production \
    stop backend frontend nginx
```

### Step 3 — Take emergency snapshot

```bash
# Even a corrupt DB may have recent data worth preserving
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" \
    | gzip -9 > /opt/kaasb/backups/db/emergency-$(date +%Y%m%d%H%M%S).sql.gz
```

### Step 4 — Select the correct backup

```bash
ls -lht /opt/kaasb/backups/db/kaasb-db-daily-*.sql.gz | head -10
# Pick the most recent backup that predates the corruption event

BACKUP_FILE="/opt/kaasb/backups/db/kaasb-db-daily-YYYYMMDD-HHMMSS.sql.gz"

# Verify checksum
sha256sum -c "${BACKUP_FILE%.sql.gz}.sha256"
```

### Step 5 — Restore

```bash
bash /opt/kaasb/scripts/restore.sh --db "${BACKUP_FILE}"
```

### Step 6 — Verify financial integrity

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec db psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT
    (SELECT COUNT(*) FROM users)            AS users,
    (SELECT COUNT(*) FROM jobs)             AS jobs,
    (SELECT COUNT(*) FROM contracts)        AS contracts,
    (SELECT COUNT(*) FROM transactions)     AS transactions,
    (SELECT SUM(amount) FROM escrows WHERE status = 'held') AS escrow_total;
"
```

### Step 7 — Restart and notify

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## Scenario 3: Accidental File Deletion

**Trigger:** User-uploaded files (avatars, attachments, portfolio items) are missing or deleted.

**RPO:** Up to 24 hours
**RTO:** 30–60 minutes

### Step 1 — Identify the scope

```bash
# Check what's currently in the uploads volume
docker run --rm -v kaasb_backend_uploads:/data alpine:3.19 \
    find /data -type f | head -50
```

### Step 2 — Restore from backup

```bash
# List available file backups
ls -lht /opt/kaasb/backups/files/

# Dry run first
bash /opt/kaasb/scripts/restore.sh \
    --files /opt/kaasb/backups/files/kaasb-files-daily-LATEST.tar.gz \
    --dry-run

# Restore (overwrites entire uploads volume)
bash /opt/kaasb/scripts/restore.sh \
    --files /opt/kaasb/backups/files/kaasb-files-daily-LATEST.tar.gz
```

### Step 3 — Partial restore (single file)

If only one file needs recovery:
```bash
# Extract just the needed file from the backup
BACKUP="/opt/kaasb/backups/files/kaasb-files-daily-LATEST.tar.gz"
tar tzf "${BACKUP}" | grep "uploads/avatar"  # find the file

# Extract specific file to /tmp
tar xzf "${BACKUP}" -C /tmp "uploads/avatars/user-uuid.jpg"

# Copy into the running volume
docker cp /tmp/uploads/avatars/user-uuid.jpg kaasb_backend:/app/uploads/avatars/
```

---

## Scenario 4: Failed Database Migration

**Trigger:** `alembic upgrade head` fails mid-migration, leaving the schema in a partially-applied state.

**RPO:** Zero (pre-migration backup should have been taken)
**RTO:** 15–60 minutes

### Step 1 — Assess current migration state

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec backend alembic current

docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec backend alembic history --verbose
```

### Step 2 — Option A: Roll back the last migration

```bash
# Roll back one step
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec backend alembic downgrade -1

# Verify
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec backend alembic current
```

### Step 3 — Option B: Restore from pre-migration backup

Use only if downgrade is unsafe (data-destroying migration):
```bash
# List pre-migration backups (taken by deploy.sh before migrating)
ls -lht /opt/kaasb/backups/db/kaasb-db-pre-* 2>/dev/null

bash /opt/kaasb/scripts/restore.sh \
    --db /opt/kaasb/backups/db/kaasb-db-pre-LATEST.sql.gz
```

### Step 4 — Fix and re-apply

```bash
# Edit the broken migration file locally, commit, push
# Then on server:
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec backend alembic upgrade head
```

### Migration rollback safety reference

| Migration | Rollback Safety | Notes |
|-----------|----------------|-------|
| `initial_schema` (a1b2c3d4e5f6) | ✅ Safe | Drop-all — no data loss if DB is empty |
| `payments` (ae6a5c343032) | ⚠ Data-dependent | Drops Qi Card columns |
| `float_to_numeric` (d1a2b3c4d5e6) | ⚠ Lossy | Float←Numeric cast; don't roll back after transactions |
| `schema_hardening` (e2b3c4d5e6f7) | ✅ Safe | Audit log drop is safe |
| `performance_indexes` (c7d4e8f2a901) | ✅ Safe | Index drop never loses data |
| `legal_compliance` (f3a4b5c6d7e8) | ✅ Safe | Reports table drop is safe |

---

## Scenario 5: Security Incident / Compromise

**Trigger:** Unauthorised access, data exfiltration, ransomware, or suspicious activity detected.

**RPO:** Up to 24 hours (last clean backup)
**RTO:** 4–8 hours (new server + forensics)

### Step 1 — Isolate immediately

```bash
# In Hetzner Console: disable the server's network interface
# OR: drop all ingress traffic via firewall
ufw default deny incoming
ufw allow from YOUR_OFFICE_IP to any port 22
ufw enable
```

### Step 2 — Preserve evidence

```bash
# Snapshot the compromised server's disk BEFORE any cleanup
# (Use Hetzner snapshot feature in the console)
# This preserves forensic evidence

# Dump running processes and network connections
ps auxf > /tmp/processes-$(date +%Y%m%d%H%M%S).txt
ss -tlnp > /tmp/connections-$(date +%Y%m%d%H%M%S).txt
last -100 > /tmp/logins-$(date +%Y%m%d%H%M%S).txt
cat /var/log/auth.log | grep -E "(Failed|Invalid|Accepted)" | tail -200 \
    > /tmp/auth-events-$(date +%Y%m%d%H%M%S).txt
```

### Step 3 — Rotate ALL credentials immediately

- [ ] Generate new `SECRET_KEY` (JWT signing key → all sessions invalidated)
- [ ] Rotate `DB_PASSWORD`
- [ ] Rotate `REDIS_PASSWORD`
- [ ] Rotate `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` via Stripe Dashboard
- [ ] Rotate Wise API key via Wise Dashboard
- [ ] Rotate GitHub repository secrets (SERVER_SSH_KEY, GHCR_TOKEN)
- [ ] Revoke and regenerate all SSH keys

### Step 4 — Rebuild on new server

Follow [Scenario 1](#scenario-1-complete-server-failure) to provision a clean server.
Do NOT restore configs from the compromised system — rebuild from scratch using the team password manager.

### Step 5 — Restore latest clean backup

```bash
# Use the backup that predates the first suspicious activity
bash /opt/kaasb/scripts/restore.sh --all
```

### Step 6 — Audit restored data

```bash
# Check for any suspicious records created during the incident window
docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec db psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT id, email, created_at, last_login_at
FROM users
WHERE created_at > 'INCIDENT_START_TIME'
ORDER BY created_at;

SELECT * FROM audit_log
WHERE changed_at > 'INCIDENT_START_TIME'
ORDER BY changed_at;
"
```

### Step 7 — Notify affected users

Per GDPR Article 33: notify the supervisory authority within 72 hours of becoming aware of the breach.
Per GDPR Article 34: notify affected individuals if the breach is likely to result in high risk.

See [Business Continuity Plan](business-continuity.md) §4 for breach notification templates.

---

## Scenario 6: Disk Full / Resource Exhaustion

**Trigger:** Containers crash-looping, PostgreSQL `no space left on device`, nginx 500 errors.

**RPO:** N/A (no data loss expected)
**RTO:** 15–30 minutes

### Step 1 — Identify what's filling the disk

```bash
ssh root@116.203.140.27

# Overall disk usage
df -h

# Find large directories
du -sh /opt/kaasb/backups/* | sort -hr | head -20
du -sh /var/lib/docker/volumes/* | sort -hr | head -20
docker system df
```

### Step 2 — Free space immediately

```bash
# Option A: Prune old Docker images and stopped containers
docker system prune -f
docker image prune -a -f  # Removes ALL unused images — be careful

# Option B: Prune excess backup files (keep last 3 instead of 7)
cd /opt/kaasb/backups/db
ls -t kaasb-db-daily-*.sql.gz | tail -n +4 | xargs rm -vf

# Option C: Trim log files
truncate -s 100M /var/log/kaasb/backup.log
journalctl --vacuum-size=500M
```

### Step 3 — Identify long-term cause

```bash
# Large Docker log files?
find /var/lib/docker/containers -name "*.log" -size +100M | xargs ls -lh

# Limit container log sizes (already set in docker-compose.prod.yml)
# If logs are large, they were set before this config was applied — truncate:
find /var/lib/docker/containers -name "*.log" -size +100M -exec truncate -s 50M {} \;

# WAL accumulation?
du -sh /var/lib/docker/volumes/kaasb_postgres_data/_data/pgdata/pg_wal/
# If large: connect to DB and run CHECKPOINT
docker compose -f /opt/kaasb/docker-compose.prod.yml --env-file /opt/kaasb/.env.production \
    exec db psql -U "${DB_USER}" -c "CHECKPOINT;"
```

### Step 4 — Expand storage (if needed)

In Hetzner Console:
1. Resize the volume or upgrade the server
2. Resize the filesystem: `resize2fs /dev/sda1`

### Step 5 — Restart affected services

```bash
cd /opt/kaasb
./deploy.sh --restart
./deploy.sh --status
```

### Step 6 — Prevent recurrence

```bash
# Verify cron is running for backup rotation
crontab -l
cat /etc/cron.d/kaasb

# Set up disk usage alert (already in monitor-backups.sh)
# Ensure monitor-backups.sh runs every 30 min
```

---

## Post-Incident Review

After every Severity Critical or High incident, complete a post-mortem within 48 hours:

1. **Timeline:** When was the incident detected? When did recovery begin/complete?
2. **Root cause:** What caused the incident?
3. **Impact:** Which users were affected? What data was lost?
4. **Recovery actions:** What was done and by whom?
5. **Preventive measures:** What changes prevent recurrence?
6. **DR drill update:** Did this incident reveal gaps in the runbook? Update this document.
