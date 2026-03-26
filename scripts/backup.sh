#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Database Backup Script
# =============================================================================
# Runs automatically via cron at 02:00 UTC daily.
# Can also be run manually: bash /opt/kaasb/scripts/backup.sh
#
# Retention policy:
#   - Daily backups: keep last 7
#   - Weekly backups (Sunday): keep last 4 (stored separately)
#   - Backup is gzip-compressed (~10× smaller than raw SQL)
#
# Optional off-site upload to S3-compatible storage (Hetzner Object Storage,
# Backblaze B2, Cloudflare R2). Set S3_BUCKET below to enable.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
LOG_FILE="/var/log/kaasb/backup.log"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.prod.yml --env-file ${ENV_FILE}"

KEEP_DAILY=7    # Daily backups to retain
KEEP_WEEKLY=4   # Weekly backups (Sundays) to retain

# Optional: S3-compatible upload (leave empty to skip)
# Example: "s3://kaasb-backups/db" or "s3://bucket-name/prefix"
S3_BUCKET=""
S3_ENDPOINT=""   # Example: "https://fsn1.your-objectstorage.com" (Hetzner)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" | tee -a "$LOG_FILE"; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || { log "ERROR: $ENV_FILE not found"; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[ -n "${DB_USER:-}"     ] || { log "ERROR: DB_USER not set"; exit 1; }
[ -n "${DB_PASSWORD:-}" ] || { log "ERROR: DB_PASSWORD not set"; exit 1; }
[ -n "${DB_NAME:-}"     ] || { log "ERROR: DB_NAME not set"; exit 1; }

mkdir -p "$BACKUP_DIR" "$( dirname "$LOG_FILE" )"

# ---------------------------------------------------------------------------
# Create backup
# ---------------------------------------------------------------------------
TIMESTAMP=$(date -u '+%Y%m%d-%H%M%S')
DOW=$(date -u '+%u')  # 1=Monday … 7=Sunday
OUTFILE="${BACKUP_DIR}/kaasb-daily-${TIMESTAMP}.sql.gz"

log "Starting backup → ${OUTFILE}"

# pg_dump inside the running db container (no port exposure needed)
$COMPOSE exec -T db pg_dump \
    -U "${DB_USER}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    "${DB_NAME}" \
| gzip -9 > "${OUTFILE}"

SIZE=$(du -sh "${OUTFILE}" | cut -f1)
log "Backup complete: ${SIZE}"

# ---------------------------------------------------------------------------
# Weekly copy (every Sunday = DOW 7)
# ---------------------------------------------------------------------------
if [ "$DOW" -eq 7 ]; then
    WEEKLY="${BACKUP_DIR}/kaasb-weekly-$(date -u '+%Y-W%V').sql.gz"
    cp "${OUTFILE}" "${WEEKLY}"
    log "Weekly backup saved: $(basename "${WEEKLY}")"

    # Rotate weekly backups
    find "${BACKUP_DIR}" -name "kaasb-weekly-*.sql.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_WEEKLY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -v >> "$LOG_FILE" 2>&1
fi

# ---------------------------------------------------------------------------
# Rotate daily backups (keep KEEP_DAILY most recent)
# ---------------------------------------------------------------------------
find "${BACKUP_DIR}" -name "kaasb-daily-*.sql.gz" -printf '%T@ %p\n' \
    | sort -rn | tail -n +$(( KEEP_DAILY + 1 )) | cut -d' ' -f2- \
    | xargs -r rm -v >> "$LOG_FILE" 2>&1

log "Retention applied: keeping last ${KEEP_DAILY} daily + ${KEEP_WEEKLY} weekly backups"

# ---------------------------------------------------------------------------
# Optional: upload to S3-compatible storage
# ---------------------------------------------------------------------------
if [ -n "${S3_BUCKET}" ]; then
    log "Uploading to ${S3_BUCKET}..."
    if command -v aws &>/dev/null; then
        ENDPOINT_ARGS=""
        [ -n "${S3_ENDPOINT}" ] && ENDPOINT_ARGS="--endpoint-url ${S3_ENDPOINT}"
        # shellcheck disable=SC2086
        aws s3 cp "${OUTFILE}" "${S3_BUCKET}/$(basename "${OUTFILE}")" \
            $ENDPOINT_ARGS \
            --storage-class STANDARD_IA \
            --quiet
        log "Upload complete: ${S3_BUCKET}/$(basename "${OUTFILE}")"

        # Also sync weekly if today is Sunday
        if [ "$DOW" -eq 7 ]; then
            # shellcheck disable=SC2086
            aws s3 cp "${WEEKLY}" "${S3_BUCKET}/weekly/$(basename "${WEEKLY}")" \
                $ENDPOINT_ARGS --quiet
        fi

        # Delete S3 objects older than KEEP_DAILY+3 days from the daily prefix
        # (AWS CLI lifecycle rules are more reliable — set them in the console)
    else
        log "WARN: S3_BUCKET is set but 'aws' CLI not found — skipping upload"
    fi
fi

# ---------------------------------------------------------------------------
# Disk space check
# ---------------------------------------------------------------------------
DISK_USED=$(df -h "${BACKUP_DIR}" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "${DISK_USED}" -gt 80 ]; then
    log "WARN: Disk usage is ${DISK_USED}% — consider pruning backups or expanding storage"
fi

# ---------------------------------------------------------------------------
# Integrity verification — test the backup is a valid gzip + SQL structure
# ---------------------------------------------------------------------------
log "Verifying backup integrity..."

# 1. Check gzip integrity (detects truncated / corrupt archives)
if ! gzip -t "${OUTFILE}" 2>/dev/null; then
    log "ERROR: Backup file is corrupt (gzip integrity check failed): ${OUTFILE}"
    exit 1
fi

# 2. Spot-check that the SQL content looks valid
#    A real pg_dump always starts with "-- PostgreSQL database dump"
HEADER_LINE=$(zcat "${OUTFILE}" 2>/dev/null | head -1)
if [[ "$HEADER_LINE" != *"PostgreSQL database dump"* ]]; then
    log "ERROR: Backup does not appear to be a valid pg_dump file. Header: ${HEADER_LINE}"
    exit 1
fi

# 3. Verify at least one CREATE TABLE statement is present
TABLE_COUNT=$(zcat "${OUTFILE}" 2>/dev/null | grep -c "^CREATE TABLE" || true)
if [ "${TABLE_COUNT:-0}" -eq 0 ]; then
    log "ERROR: Backup contains no CREATE TABLE statements — likely empty or wrong database"
    exit 1
fi
log "Integrity OK: ${TABLE_COUNT} CREATE TABLE statements found in backup"

# 4. Write SHA-256 checksum file alongside the backup (used to verify before restore)
CHECKSUM_FILE="${OUTFILE%.sql.gz}.sha256"
sha256sum "${OUTFILE}" > "${CHECKSUM_FILE}"
log "Checksum written: $(basename "${CHECKSUM_FILE}")"

# 5. Record backup metadata for monitoring queries (db-monitoring.sql section 9)
#    Append to a simple CSV log that can be queried or imported into the database.
METADATA_LOG="${BACKUP_DIR}/backup_history.csv"
if [ ! -f "$METADATA_LOG" ]; then
    echo "backup_type,file_name,file_size_bytes,table_count,completed_at" > "$METADATA_LOG"
fi
FILE_SIZE=$(stat -c %s "${OUTFILE}" 2>/dev/null || echo 0)
echo "daily,$(basename "${OUTFILE}"),${FILE_SIZE},${TABLE_COUNT},$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$METADATA_LOG"

# 6. Alert if backup is too small (< 10 KB is suspicious for a real DB)
if [ "${FILE_SIZE}" -lt 10240 ]; then
    log "WARN: Backup file is unusually small (${FILE_SIZE} bytes) — verify the database is not empty"
fi

log "Backup job finished successfully"
