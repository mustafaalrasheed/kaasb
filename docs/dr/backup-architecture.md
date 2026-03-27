# Kaasb Platform — Backup Architecture

**Last updated:** 2026-03-27

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Hetzner CPX22 — 116.203.140.27                   │
│                                                                     │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐                │
│  │ PostgreSQL │   │  backend   │   │    nginx     │                │
│  │  (kaasb_db)│   │  (FastAPI) │   │  (reverse    │                │
│  │            │   │            │   │   proxy)     │                │
│  └─────┬──────┘   └─────┬──────┘   └──────────────┘                │
│        │                │                                           │
│        │ pg_dump        │ Docker volume                             │
│        │ (docker exec)  │ backend_uploads                           │
│        ▼                ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  scripts/backup.sh (cron 02:00 UTC)          │  │
│  │                                                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │  │
│  │  │ DB backup   │  │ Files backup │  │  Config backup     │  │  │
│  │  │ (pg_dump    │  │ (tar uploads │  │  (.env, nginx.conf,│  │  │
│  │  │  + gzip)    │  │  volume)     │  │  docker-compose,   │  │  │
│  │  └──────┬──────┘  └──────┬───────┘  │  SSL certs)        │  │  │
│  │         │                │          └────────┬───────────┘  │  │
│  │         └────────────────┴───────────────────┘              │  │
│  │                          │                                   │  │
│  │         gzip -t + sha256sum + SQL structure check            │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│               ┌─────────────▼────────────────┐                     │
│               │   /opt/kaasb/backups/         │                     │
│               │   ├── db/                     │                     │
│               │   │   ├── kaasb-db-daily-*    │                     │
│               │   │   ├── kaasb-db-weekly-*   │                     │
│               │   │   └── kaasb-db-monthly-*  │                     │
│               │   ├── files/                  │                     │
│               │   │   ├── kaasb-files-daily-* │                     │
│               │   │   └── ...                 │                     │
│               │   ├── configs/                │                     │
│               │   │   ├── kaasb-configs-*     │                     │
│               │   │   └── ...                 │                     │
│               │   └── backup_history.csv      │                     │
│               └─────────────┬────────────────-┘                     │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  S3-compatible     │
                    │  Object Storage    │   ← Optional off-site
                    │  (Hetzner / B2 /   │     (S3_BUCKET env var)
                    │   Cloudflare R2)   │
                    └────────────────────┘
```

---

## Backup Script Flow

```
backup.sh
    │
    ├── [1/3] Database
    │       ├── pg_dump (inside kaasb_db container) | gzip -9
    │       ├── gzip -t integrity check
    │       ├── SQL header validation
    │       ├── CREATE TABLE count check
    │       ├── sha256sum checksum
    │       ├── Sunday → weekly copy
    │       ├── 1st of month → monthly copy
    │       ├── Rotation (keep 7 daily / 4 weekly / 12 monthly)
    │       ├── Optional GPG encryption
    │       └── Optional S3 upload
    │
    ├── [2/3] User Files
    │       ├── docker run alpine tar czf (from backend_uploads volume)
    │       ├── gzip -t integrity check
    │       ├── sha256sum checksum
    │       ├── Sunday → weekly copy
    │       ├── 1st of month → monthly copy
    │       ├── Rotation (keep 7 daily / 4 weekly / 12 monthly)
    │       └── Optional S3 upload
    │
    ├── [3/3] Configs
    │       ├── Copy: .env.production, nginx.conf, postgresql.conf
    │       ├── Copy: docker-compose.prod.yml, docker-compose.monitoring.yml
    │       ├── Copy: alertmanager.yml, deploy.sh, cron files
    │       ├── docker run alpine tar (SSL certs from letsencrypt volume)
    │       ├── Package all into tar.gz
    │       ├── sha256sum checksum
    │       ├── Rotation (keep 7 daily / 4 weekly / 12 monthly)
    │       └── Optional S3 upload
    │
    └── Disk space check + CSV audit log entry
```

---

## Cron Configuration

Install at `/etc/cron.d/kaasb` on the production server:

```cron
# /etc/cron.d/kaasb
# Kaasb Platform — Scheduled jobs
# All times are UTC

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# ─── Backup ──────────────────────────────────────────────────────────────────
# Full backup (DB + files + configs) every day at 02:00 UTC
0 2 * * * root bash /opt/kaasb/scripts/backup.sh >> /var/log/kaasb/backup.log 2>&1

# ─── Backup Monitoring ────────────────────────────────────────────────────────
# Health check every 30 minutes — alerts if backup is stale or disk is full
*/30 * * * * root bash /opt/kaasb/scripts/monitor-backups.sh >> /var/log/kaasb/backup-monitor.log 2>&1

# ─── Backup Verification (live restore test) ──────────────────────────────────
# Full integrity check + live restore to temp container on 1st of each month at 04:00 UTC
0 4 1 * * root bash /opt/kaasb/scripts/backup-verify.sh >> /var/log/kaasb/backup-verify.log 2>&1

# ─── Data Retention ───────────────────────────────────────────────────────────
# GDPR data retention enforcement — runs daily at 03:00 UTC
0 3 * * * root docker compose -f /opt/kaasb/docker-compose.prod.yml \
  --env-file /opt/kaasb/.env.production \
  exec -T backend python -m app.tasks.data_retention >> /var/log/kaasb/retention.log 2>&1

# ─── Database Maintenance ─────────────────────────────────────────────────────
# Weekly VACUUM ANALYZE — Sunday at 03:30 UTC (low traffic window)
30 3 * * 0 root docker compose -f /opt/kaasb/docker-compose.prod.yml \
  --env-file /opt/kaasb/.env.production \
  exec -T db psql -U kaasb_user -d kaasb_db -c "VACUUM ANALYZE;" >> /var/log/kaasb/vacuum.log 2>&1

# ─── Log Rotation ─────────────────────────────────────────────────────────────
# Trim kaasb log files if they exceed 200 MB — daily at 01:00 UTC
0 1 * * * root find /var/log/kaasb -name "*.log" -size +200M \
  -exec truncate -s 100M {} \; 2>/dev/null
```

**Install on server:**
```bash
scp docs/dr/backup-architecture.md root@116.203.140.27:/tmp/
# Then on the server, extract the cron block and install:
cat > /etc/cron.d/kaasb << 'CRON'
# ... paste cron block above ...
CRON
chmod 644 /etc/cron.d/kaasb
```

---

## Backup Retention Summary

| Component | Daily | Weekly | Monthly | Total max files | Approx. storage |
|-----------|-------|--------|---------|-----------------|----------------|
| Database | 7 | 4 | 12 | 23 | ~230 MB (10 MB/dump) |
| User files | 7 | 4 | 12 | 23 | Varies with uploads |
| Configs | 7 | 4 | 12 | 23 | ~5 MB (small) |

> Estimate: a Kaasb database with 10,000 users and 50,000 records is approximately 50–100 MB uncompressed, ~5–10 MB gzipped.

---

## Security Considerations

### At-rest encryption

Set `BACKUP_GPG_KEY` in `.env.production` to enable GPG encryption of all backup files before S3 upload:

```bash
# Generate a GPG key pair for backups
gpg --batch --gen-key << EOF
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Kaasb Backups
Name-Email: backups@kaasb.com
Expire-Date: 2y
%no-passphrase
%commit
EOF

# Get the key ID
gpg --list-keys backups@kaasb.com

# Set in .env.production
echo 'BACKUP_GPG_KEY=backups@kaasb.com' >> /opt/kaasb/.env.production

# Export and store the PRIVATE key in your team password manager
gpg --armor --export-secret-keys backups@kaasb.com > /tmp/kaasb-backup-key.asc
# Store this in 1Password / Vault — it's the only way to decrypt backups
rm -f /tmp/kaasb-backup-key.asc
```

### Access control

- Backup directory (`/opt/kaasb/backups/`) should be owned by `root:root` with `700` permissions
- S3 bucket should have a dedicated IAM user with `PutObject` only (no `DeleteObject` without MFA)
- Backup verify script runs in an isolated container — no production data risk

### Off-site backup (recommended before production launch)

Configure one of:
```bash
# Option A: Hetzner Object Storage
S3_BUCKET="s3://kaasb-backups"
S3_ENDPOINT="https://fsn1.your-objectstorage.com"

# Option B: Backblaze B2
S3_BUCKET="s3://kaasb-backups"
S3_ENDPOINT="https://s3.us-west-004.backblazeb2.com"

# Option C: Cloudflare R2
S3_BUCKET="s3://kaasb-backups"
S3_ENDPOINT="https://<account-id>.r2.cloudflarestorage.com"
```

Add `S3_BUCKET`, `S3_ENDPOINT`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` to `.env.production`.

---

## Monitoring Integration

`monitor-backups.sh` integrates with:

| Channel | Config | Trigger |
|---------|--------|---------|
| Log file | Always | Every run |
| Slack / webhook | Set `ALERT_WEBHOOK` in `.env.production` | WARN or CRIT |
| Email | Set `ALERT_EMAIL` in `.env.production` | WARN or CRIT |
| Sentry | Uses existing `SENTRY_DSN` | CRIT only |
| Grafana | Import `backup_history.csv` as CSV data source | Dashboard |

`backup_history.csv` schema:
```
backup_type, file_name, file_size_bytes, detail, completed_at
db-daily,    kaasb-db-daily-20260327-020001.sql.gz, 8388608, tables=22, 2026-03-27T02:00:45Z
files-daily, kaasb-files-daily-20260327-020010.tar.gz, 1048576, upload_files, 2026-03-27T02:00:55Z
configs-daily,kaasb-configs-daily-20260327-020015.tar.gz, 51200, env+nginx+certs, 2026-03-27T02:01:00Z
verify,      verify-20260401-040001, 0, pass=12 warn=0 fail=0, 2026-04-01T04:00:30Z
```
