# Kaasb Platform — Database Disaster Recovery Plan

**Last updated:** 2026-03-26
**Applies to:** Production PostgreSQL database on Hetzner CPX22
**Owner:** Platform Engineering / DBA On-Call

---

## Objectives

| Metric | Target | Basis |
|--------|--------|-------|
| **RPO** (Recovery Point Objective) | ≤ 24 hours | Daily compressed pg_dump + WAL archiving |
| **RTO** (Recovery Time Objective) | ≤ 4 hours | Restore + verify + restart on same or new server |
| **Backup retention** | 7 daily + 4 weekly | Configured in `scripts/backup.sh` |
| **Backup location** | Local `/opt/kaasb/backups/` + optional S3 | Off-site if S3_BUCKET is configured |

> To achieve RPO < 1 hour: enable WAL archiving (see Section 5).
> To achieve RTO < 1 hour: set up a hot standby replica (not yet configured).

---

## Disaster Scenario Matrix

| Scenario | Severity | Recovery Approach | Estimated RTO |
|----------|----------|-------------------|---------------|
| Single table accidentally dropped | Critical | Restore from backup + replay app logs | 2–4 hours |
| Full database corruption | Critical | Full restore from latest backup | 3–4 hours |
| Server hardware failure | Critical | Spin up new server + restore backup | 3–5 hours |
| Alembic migration gone wrong | High | `alembic downgrade -1` or restore | 15–60 min |
| Runaway query caused data change | High | Point-in-time restore (if WAL enabled) | 2–3 hours |
| Accidental user deletion (soft-deleted) | Medium | UPDATE users SET deleted_at = NULL | 5 min |
| Connection pool exhaustion | Medium | Restart API workers, investigate | 5–15 min |
| Disk full (backups or PGDATA) | Medium | Free space + restart services | 30–60 min |

---

## Section 1: Pre-Disaster Preparedness

### 1.1 Verify Backup Health (Daily)

```bash
# Check backup age and integrity
ls -lht /opt/kaasb/backups/kaasb-daily-*.sql.gz | head -5

# Verify checksum matches
cd /opt/kaasb/backups
sha256sum -c kaasb-daily-LATEST.sha256

# Test gzip integrity
gzip -t kaasb-daily-LATEST.sql.gz && echo "OK" || echo "CORRUPT"
```

### 1.2 Monthly Restore Test (Staging)

**Schedule:** First Sunday of each month, 03:00 UTC.

```bash
# On staging server (never on production):
bash /opt/kaasb/scripts/restore-db.sh /opt/kaasb/backups/kaasb-daily-LATEST.sql.gz staging_kaasb

# Verify table counts match production
psql -U kaasb_user -d staging_kaasb -c "
SELECT table_name,
       (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) AS c FROM '||quote_ident(table_name), false, true, '')))[1]::text::int AS row_count
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"
```

### 1.3 Key Credentials & Access

Store these in your secrets manager (not in code):

| Item | Where to find |
|------|--------------|
| DB root password | `.env.production` → `DB_PASSWORD` |
| DB superuser (postgres) | Docker volume / Hetzner console |
| SSH access to server | SSH key in team password manager |
| S3 backup credentials | `.env.production` → `AWS_ACCESS_KEY_ID` |
| Hetzner console login | Team 1Password vault |

---

## Section 2: Full Database Restore

### 2.1 When to Use
- Complete data loss or corruption
- Server hardware failure
- Ransomware / security incident

### 2.2 Step-by-Step Restore Procedure

**Step 1: Confirm the extent of damage**
```bash
# Can you still connect?
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql -U kaasb_user -d kaasb_db -c "\l"

# Check error logs
docker compose -f /opt/kaasb/docker-compose.prod.yml logs db --tail=100
```

**Step 2: Take a pre-restore snapshot (if DB is still accessible)**
```bash
# Even a corrupt DB may have some recent data worth preserving
pg_dump -U kaasb_user -d kaasb_db --format=plain | gzip > /tmp/pre-restore-$(date +%Y%m%d%H%M%S).sql.gz
```

**Step 3: Stop application traffic**
```bash
# Stop API workers (keeps DB running for the restore)
docker compose -f /opt/kaasb/docker-compose.prod.yml stop api

# Optional: put up maintenance page via Nginx
```

**Step 4: Select backup to restore**
```bash
ls -lht /opt/kaasb/backups/kaasb-daily-*.sql.gz | head -10
# Pick the most recent backup that predates the incident

BACKUP_FILE="/opt/kaasb/backups/kaasb-daily-YYYYMMDD-HHMMSS.sql.gz"

# Verify checksum before restore
sha256sum -c "${BACKUP_FILE%.sql.gz}.sha256" || { echo "CHECKSUM MISMATCH — backup may be corrupt"; exit 1; }
```

**Step 5: Drop and recreate the database**
```bash
# Terminate all existing connections first
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql \
    -U postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'kaasb_db' AND pid <> pg_backend_pid();
"

# Drop and recreate
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql \
    -U postgres -c "DROP DATABASE IF EXISTS kaasb_db;"
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql \
    -U postgres -c "CREATE DATABASE kaasb_db OWNER kaasb_user;"
```

**Step 6: Restore from backup**
```bash
# Stream backup into database (avoids temp file)
zcat "$BACKUP_FILE" | docker compose -f /opt/kaasb/docker-compose.prod.yml exec -T db \
    psql -U kaasb_user -d kaasb_db

echo "Exit code: $?"  # Must be 0
```

**Step 7: Run pending migrations**
```bash
docker compose -f /opt/kaasb/docker-compose.prod.yml exec api \
    alembic upgrade head
```

**Step 8: Verify restore integrity**
```bash
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql \
    -U kaasb_user -d kaasb_db -c "
SELECT table_name,
       (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) AS c FROM '||quote_ident(table_name), false, true, '')))[1]::text::int AS row_count
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

# Should show rows in: users, jobs, contracts, proposals, milestones,
# transactions, escrows, reviews, messages, conversations, notifications
```

**Step 9: Verify financial integrity**
```bash
# Run the business health checks from db-monitoring.sql
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db psql \
    -U kaasb_user -d kaasb_db -f /opt/kaasb/scripts/db-monitoring.sql 2>&1 | grep -A3 "Section 10"
```

**Step 10: Restart application**
```bash
docker compose -f /opt/kaasb/docker-compose.prod.yml start api

# Watch startup logs
docker compose -f /opt/kaasb/docker-compose.prod.yml logs api -f --tail=50

# Verify health endpoint
curl -sf https://api.kaasb.com/health | jq .
```

**Step 11: Communicate to stakeholders**
```
Subject: [Kaasb] Database restored — service resuming

Timeline:
  - Incident detected: [TIME]
  - Service suspended: [TIME]
  - Restore completed: [TIME]
  - Service resumed: [TIME]

Data loss window: from [BACKUP_TIMESTAMP] to [INCIDENT_TIME]
Affected records: [describe what may be missing]
Next steps: [monitoring period, root cause investigation]
```

---

## Section 3: Migration Rollback

### 3.1 Emergency Rollback Procedure

```bash
# Check current state
docker compose -f /opt/kaasb/docker-compose.prod.yml exec api alembic current

# Roll back the last migration
docker compose -f /opt/kaasb/docker-compose.prod.yml exec api alembic downgrade -1

# Verify
docker compose -f /opt/kaasb/docker-compose.prod.yml exec api alembic current

# Restart API to pick up schema changes
docker compose -f /opt/kaasb/docker-compose.prod.yml restart api
```

### 3.2 Migration-Specific Rollback Notes

| Migration | Rollback Safety | Notes |
|-----------|----------------|-------|
| `d1a2b3c4d5e6` (Float→Numeric) | ⚠ Lossy | Numeric→Float cast preserves values but loses decimal guarantees. Do NOT roll back after financial transactions occur. |
| `e2b3c4d5e6f7` (schema hardening) | ✅ Safe | Dropping audit_log is safe. Removing deleted_at loses soft-delete state. |
| `c7d4e8f2a901` (performance indexes) | ✅ Safe | Dropping indexes never loses data, only slows queries. |
| `ae6a5c343032` (qi_card) | ⚠ Data-dependent | Dropping qi_card columns loses Qi Card account data. |
| `b3f9e2a1c456` (token_version) | ✅ Safe | Removes column, invalidates all existing access tokens (all users re-login). |

---

## Section 4: Point-in-Time Recovery (PITR)

> **Requires:** `archive_mode = on` and `archive_command` configured in PostgreSQL.
> **Purpose:** Recover to any second in time, not just the last backup.

### 4.1 Setup WAL Archiving (One-time)

```bash
# 1. Create archive directory on server
mkdir -p /opt/kaasb/wal_archive
chown postgres:postgres /opt/kaasb/wal_archive

# 2. In postgresql.conf, enable:
#    wal_level = replica
#    archive_mode = on
#    archive_command = 'test ! -f /opt/kaasb/wal_archive/%f && cp %p /opt/kaasb/wal_archive/%f'

# 3. Restart PostgreSQL
docker compose -f /opt/kaasb/docker-compose.prod.yml restart db

# 4. Take base backup (required as starting point for PITR)
docker compose -f /opt/kaasb/docker-compose.prod.yml exec db \
    pg_basebackup -D /opt/kaasb/base_backup -Fp -Xs -P -U postgres
```

### 4.2 PITR Restore Procedure

```bash
# Identify target recovery time (e.g., "2026-03-26 14:30:00 UTC")
TARGET_TIME="2026-03-26 14:30:00+00"

# 1. Stop PostgreSQL
docker compose -f /opt/kaasb/docker-compose.prod.yml stop db

# 2. Replace PGDATA with base backup
cp -a /var/lib/docker/volumes/kaasb_pgdata/_data /opt/kaasb/pgdata_corrupted
rsync -a /opt/kaasb/base_backup/ /var/lib/docker/volumes/kaasb_pgdata/_data/

# 3. Create recovery signal file
touch /var/lib/docker/volumes/kaasb_pgdata/_data/recovery.signal

# 4. Add recovery target to postgresql.conf
echo "restore_command = 'cp /opt/kaasb/wal_archive/%f %p'" \
    >> /var/lib/docker/volumes/kaasb_pgdata/_data/postgresql.conf
echo "recovery_target_time = '${TARGET_TIME}'" \
    >> /var/lib/docker/volumes/kaasb_pgdata/_data/postgresql.conf
echo "recovery_target_action = 'promote'" \
    >> /var/lib/docker/volumes/kaasb_pgdata/_data/postgresql.conf

# 5. Start PostgreSQL (will replay WAL up to target time)
docker compose -f /opt/kaasb/docker-compose.prod.yml start db

# 6. Monitor recovery progress
docker compose -f /opt/kaasb/docker-compose.prod.yml logs db -f | grep -E "(recovery|archive|LOG)"
```

---

## Section 5: Server Total Loss (New Server)

### 5.1 Prerequisites
- Latest backup accessible (local USB, S3, or team file share)
- Server credentials available
- Docker + Docker Compose installed on new server

### 5.2 Procedure

```bash
# On new Hetzner server:

# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Clone infrastructure (or restore from git)
git clone https://github.com/your-org/kaasb /opt/kaasb
cd /opt/kaasb

# 3. Restore .env.production from secrets manager
# (must include DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY, etc.)

# 4. Start database only first
docker compose -f docker-compose.prod.yml up -d db
sleep 10

# 5. Create database user and database
docker compose -f docker-compose.prod.yml exec db psql -U postgres -c "
    CREATE USER kaasb_user WITH PASSWORD '${DB_PASSWORD}';
    CREATE DATABASE kaasb_db OWNER kaasb_user;
"

# 6. Copy backup file to new server and restore
scp backup-file.sql.gz user@new-server:/opt/kaasb/backups/
bash /opt/kaasb/scripts/restore-db.sh /opt/kaasb/backups/backup-file.sql.gz kaasb_db

# 7. Start remaining services
docker compose -f docker-compose.prod.yml up -d

# 8. Update DNS (kaasb.com A record → new server IP)
# Propagation: 1-24 hours depending on TTL
```

---

## Section 6: Runbook for Common Incidents

### 6.1 High Connection Count Alert

```bash
# See who's connected
psql -c "SELECT application_name, state, COUNT(*) FROM pg_stat_activity
         WHERE datname='kaasb_db' GROUP BY 1,2 ORDER BY 3 DESC;"

# Kill idle connections > 10 minutes
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
         WHERE datname='kaasb_db' AND state='idle'
         AND state_change < now() - INTERVAL '10 minutes';"

# Restart API workers to release all connections cleanly
docker compose -f docker-compose.prod.yml restart api
```

### 6.2 Disk Full Alert

```bash
# Find large files
du -sh /var/lib/docker/volumes/kaasb_pgdata/* | sort -hr | head -20

# Clean old backups (keeping last 3)
ls -t /opt/kaasb/backups/kaasb-daily-*.sql.gz | tail -n +4 | xargs rm -v

# Check PostgreSQL WAL size
du -sh /var/lib/docker/volumes/kaasb_pgdata/_data/pg_wal/

# Force checkpoint to clean WAL
psql -c "CHECKPOINT;"
```

### 6.3 Runaway Query Killing Performance

```bash
# Find and kill
psql -c "SELECT pid, query_start, LEFT(query,100) FROM pg_stat_activity
         WHERE state='active' AND query_start < now() - INTERVAL '30 seconds';"

# Kill specific PID
psql -c "SELECT pg_terminate_backend(PID_HERE);"
```

### 6.4 Transaction ID Wraparound Emergency

```bash
# Check age (CRITICAL if > 1.5 billion)
psql -c "SELECT relname, age(relfrozenxid) FROM pg_class
         WHERE relkind='r' ORDER BY age(relfrozenxid) DESC LIMIT 10;"

# Emergency freeze (run during maintenance window)
psql -c "VACUUM FREEZE ANALYZE users;"
psql -c "VACUUM FREEZE ANALYZE transactions;"
psql -c "VACUUM FREEZE ANALYZE escrows;"
```

---

## Section 7: Monitoring & Alerting Setup

### 7.1 Recommended Cron Schedule

```cron
# /etc/cron.d/kaasb-db

# Daily backup at 02:00 UTC
0 2 * * * root bash /opt/kaasb/scripts/backup.sh >> /var/log/kaasb/backup.log 2>&1

# Hourly connection health check (send alert if > 85% connections used)
15 * * * * root PGPASSWORD="$DB_PASSWORD" psql -U kaasb_user -d kaasb_db -c \
  "SELECT CASE WHEN 100*COUNT(*)/75 > 85 THEN 'ALERT' ELSE 'OK' END \
   FROM pg_stat_activity WHERE datname='kaasb_db';" \
  | grep ALERT && curl -s "https://alerts.kaasb.com/db-connections" || true

# Weekly VACUUM ANALYZE (Sunday 03:30 UTC, low traffic)
30 3 * * 0 root PGPASSWORD="$DB_PASSWORD" psql -U kaasb_user -d kaasb_db \
  -c "VACUUM ANALYZE;" >> /var/log/kaasb/vacuum.log 2>&1
```

### 7.2 Critical Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Connection count | 75% | 90% | Restart API workers |
| Backup age | 25h | 48h | Run `backup.sh` manually |
| Dead tuple % | 20% | 40% | `VACUUM ANALYZE <table>` |
| Cache hit ratio | 95% | 90% | Increase `shared_buffers` |
| Disk free | 20% | 10% | Prune backups / expand disk |
| XID age | 750M | 1.5B | `VACUUM FREEZE` immediately |
| Replication lag | 100MB | 1GB | Investigate replica |

---

## Contacts & Escalation

| Role | Responsibility | Contact |
|------|---------------|---------|
| Primary DBA | Migration planning, performance | [team lead] |
| DevOps On-Call | Server issues, disk space | [devops] |
| Business Owner | Stakeholder communication | [business owner] |
| Hetzner Support | Hardware/network failures | console.hetzner.cloud |
