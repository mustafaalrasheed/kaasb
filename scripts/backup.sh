#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Full Backup Script
# =============================================================================
# Backs up three things:
#   1. PostgreSQL database (pg_dump → gzip)
#   2. User-uploaded files (Docker volume backend_uploads → tar.gz)
#   3. Configuration files (.env.production, nginx.conf, docker-compose, SSL)
#
# Retention policy:
#   - Daily  backups: keep last 7
#   - Weekly backups (Sunday): keep last 4
#   - Monthly backups (1st of month): keep last 12
#
# Optional:
#   - Off-site upload to S3-compatible storage (set S3_BUCKET)
#   - GPG encryption (set BACKUP_GPG_KEY)
#
# Cron schedule (add to /etc/cron.d/kaasb):
#   0 2 * * * root bash /opt/kaasb/scripts/backup.sh >> /var/log/kaasb/backup.log 2>&1
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

KEEP_DAILY=7      # Daily backups to retain
KEEP_WEEKLY=4     # Weekly backups (Sundays) to retain
KEEP_MONTHLY=12   # Monthly backups (1st of month) to retain

# Optional: S3-compatible upload (leave empty to skip)
S3_BUCKET="${S3_BUCKET:-}"
S3_ENDPOINT="${S3_ENDPOINT:-}"   # e.g. "https://fsn1.your-objectstorage.com" (Hetzner)

# Optional: GPG encryption (leave empty to skip)
# Set to GPG key ID or email: e.g. "backups@kaasb.com"
BACKUP_GPG_KEY="${BACKUP_GPG_KEY:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
log()  { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [INFO]  $*" | tee -a "$LOG_FILE"; }
warn() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [WARN]  $*" | tee -a "$LOG_FILE"; }
err()  { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [ERROR] $*" | tee -a "$LOG_FILE" >&2; }

# Encrypt file with GPG if key is configured; writes <file>.gpg and removes original
encrypt_if_configured() {
    local file="$1"
    if [ -n "${BACKUP_GPG_KEY}" ]; then
        gpg --batch --yes --recipient "${BACKUP_GPG_KEY}" \
            --output "${file}.gpg" --encrypt "${file}"
        rm -f "${file}"
        echo "${file}.gpg"
    else
        echo "${file}"
    fi
}

# Write SHA-256 checksum alongside a backup file
write_checksum() {
    local file="$1"
    sha256sum "${file}" > "${file%.sql.gz}.sha256" 2>/dev/null \
        || sha256sum "${file}" > "${file}.sha256"
    log "Checksum written: $(basename "${file}.sha256")"
}

# Upload file to S3 (if configured)
s3_upload() {
    local file="$1"
    local prefix="${2:-daily}"
    if [ -n "${S3_BUCKET}" ] && command -v aws &>/dev/null; then
        local endpoint_args=""
        [ -n "${S3_ENDPOINT}" ] && endpoint_args="--endpoint-url ${S3_ENDPOINT}"
        # shellcheck disable=SC2086
        aws s3 cp "${file}" "${S3_BUCKET}/${prefix}/$(basename "${file}")" \
            $endpoint_args --storage-class STANDARD_IA --quiet
        log "Uploaded to S3: ${S3_BUCKET}/${prefix}/$(basename "${file}")"
    elif [ -n "${S3_BUCKET}" ]; then
        warn "S3_BUCKET set but 'aws' CLI not found — skipping upload"
    fi
}

# Record an entry in the CSV audit log
record_metadata() {
    local type="$1" file="$2" size="$3" detail="$4"
    local metadata_log="${BACKUP_DIR}/backup_history.csv"
    if [ ! -f "$metadata_log" ]; then
        echo "backup_type,file_name,file_size_bytes,detail,completed_at" > "$metadata_log"
    fi
    echo "${type},$(basename "${file}"),${size},${detail},$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        >> "$metadata_log"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || { err "$ENV_FILE not found"; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[ -n "${DB_USER:-}"     ] || { err "DB_USER not set";     exit 1; }
[ -n "${DB_PASSWORD:-}" ] || { err "DB_PASSWORD not set"; exit 1; }
[ -n "${DB_NAME:-}"     ] || { err "DB_NAME not set";     exit 1; }

mkdir -p "${BACKUP_DIR}/db" "${BACKUP_DIR}/files" "${BACKUP_DIR}/configs" \
    "$( dirname "$LOG_FILE" )"

TIMESTAMP=$(date -u '+%Y%m%d-%H%M%S')
DOW=$(date -u '+%u')   # 1=Mon … 7=Sun
DOM=$(date -u '+%d')   # Day of month (01–31)

log "========================================================"
log "  Kaasb backup started — ${TIMESTAMP}"
log "========================================================"

# ---------------------------------------------------------------------------
# 1. DATABASE BACKUP
# ---------------------------------------------------------------------------
log "[1/3] Database backup..."

DB_OUTFILE="${BACKUP_DIR}/db/kaasb-db-daily-${TIMESTAMP}.sql.gz"

$COMPOSE exec -T db pg_dump \
    -U "${DB_USER}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    "${DB_NAME}" \
| gzip -9 > "${DB_OUTFILE}"

DB_SIZE=$(du -sh "${DB_OUTFILE}" | cut -f1)
log "Database dump: ${DB_SIZE} → $(basename "${DB_OUTFILE}")"

# Integrity verification
if ! gzip -t "${DB_OUTFILE}" 2>/dev/null; then
    err "Database backup corrupt (gzip test failed): ${DB_OUTFILE}"; exit 1
fi

# pg_dump --format=plain output starts with:
#   --
#   -- PostgreSQL database dump
#   --
# The marker is on line 2, not line 1. Scan the first 20 lines so we're
# robust to future pg_dump tweaks. Disable pipefail locally so zcat getting
# SIGPIPE when head/grep exit early doesn't falsely fail the check — we
# only care about grep's decision.
set +o pipefail
if ! zcat "${DB_OUTFILE}" 2>/dev/null | head -20 | grep -q "PostgreSQL database dump"; then
    set -o pipefail
    err "Database backup header check failed for ${DB_OUTFILE}"
    exit 1
fi
set -o pipefail

TABLE_COUNT=$(zcat "${DB_OUTFILE}" 2>/dev/null | grep -c "^CREATE TABLE" || true)
if [ "${TABLE_COUNT:-0}" -eq 0 ]; then
    err "Database backup contains no CREATE TABLE statements"; exit 1
fi
log "Integrity OK: ${TABLE_COUNT} tables"

# Checksum
sha256sum "${DB_OUTFILE}" > "${DB_OUTFILE%.sql.gz}.sha256"
log "Checksum: $(basename "${DB_OUTFILE%.sql.gz}.sha256")"

DB_FILE_SIZE=$(stat -c %s "${DB_OUTFILE}" 2>/dev/null || echo 0)
if [ "${DB_FILE_SIZE}" -lt 10240 ]; then
    warn "Database backup unusually small (${DB_FILE_SIZE} bytes)"
fi

# Weekly copy
if [ "$DOW" -eq 7 ]; then
    DB_WEEKLY="${BACKUP_DIR}/db/kaasb-db-weekly-$(date -u '+%Y-W%V').sql.gz"
    cp "${DB_OUTFILE}" "${DB_WEEKLY}"
    sha256sum "${DB_WEEKLY}" > "${DB_WEEKLY%.sql.gz}.sha256"
    log "Weekly DB backup: $(basename "${DB_WEEKLY}")"
    s3_upload "${DB_WEEKLY}" "weekly/db"
    # Rotate weekly
    find "${BACKUP_DIR}/db" -name "kaasb-db-weekly-*.sql.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_WEEKLY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
fi

# Monthly copy (1st of month)
if [ "$DOM" -eq 1 ]; then
    DB_MONTHLY="${BACKUP_DIR}/db/kaasb-db-monthly-$(date -u '+%Y-%m').sql.gz"
    cp "${DB_OUTFILE}" "${DB_MONTHLY}"
    sha256sum "${DB_MONTHLY}" > "${DB_MONTHLY%.sql.gz}.sha256"
    log "Monthly DB backup: $(basename "${DB_MONTHLY}")"
    s3_upload "${DB_MONTHLY}" "monthly/db"
    # Rotate monthly
    find "${BACKUP_DIR}/db" -name "kaasb-db-monthly-*.sql.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_MONTHLY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
fi

# Rotate daily DB backups
find "${BACKUP_DIR}/db" -name "kaasb-db-daily-*.sql.gz" -printf '%T@ %p\n' \
    | sort -rn | tail -n +$(( KEEP_DAILY + 1 )) | cut -d' ' -f2- \
    | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true

# Encrypt if configured
DB_FINAL=$(encrypt_if_configured "${DB_OUTFILE}")
s3_upload "${DB_FINAL}" "daily/db"
record_metadata "db-daily" "${DB_FINAL}" "${DB_FILE_SIZE}" "tables=${TABLE_COUNT}"

# ---------------------------------------------------------------------------
# 2. USER-UPLOADED FILES BACKUP
# ---------------------------------------------------------------------------
log "[2/3] User files backup (backend_uploads volume)..."

FILES_OUTFILE="${BACKUP_DIR}/files/kaasb-files-daily-${TIMESTAMP}.tar.gz"

# Run a temporary Alpine container with the uploads volume mounted, tar the contents
docker run --rm \
    -v kaasb_backend_uploads:/data:ro \
    -v "${BACKUP_DIR}/files":/backup \
    alpine:3.19 \
    tar czf "/backup/$(basename "${FILES_OUTFILE}")" -C /data . 2>/dev/null \
    || { warn "Files backup failed (volume may be empty)"; FILES_OUTFILE=""; }

if [ -n "${FILES_OUTFILE}" ] && [ -f "${FILES_OUTFILE}" ]; then
    FILES_SIZE=$(du -sh "${FILES_OUTFILE}" | cut -f1)
    log "Files backup: ${FILES_SIZE} → $(basename "${FILES_OUTFILE}")"

    if ! gzip -t "${FILES_OUTFILE}" 2>/dev/null; then
        warn "Files backup gzip check failed — may be corrupt"
    fi

    sha256sum "${FILES_OUTFILE}" > "${FILES_OUTFILE%.tar.gz}.sha256"
    FILES_FILE_SIZE=$(stat -c %s "${FILES_OUTFILE}" 2>/dev/null || echo 0)

    # Weekly + monthly copies
    if [ "$DOW" -eq 7 ]; then
        FILES_WEEKLY="${BACKUP_DIR}/files/kaasb-files-weekly-$(date -u '+%Y-W%V').tar.gz"
        cp "${FILES_OUTFILE}" "${FILES_WEEKLY}"
        sha256sum "${FILES_WEEKLY}" > "${FILES_WEEKLY%.tar.gz}.sha256"
        log "Weekly files backup: $(basename "${FILES_WEEKLY}")"
        s3_upload "${FILES_WEEKLY}" "weekly/files"
        find "${BACKUP_DIR}/files" -name "kaasb-files-weekly-*.tar.gz" -printf '%T@ %p\n' \
            | sort -rn | tail -n +$(( KEEP_WEEKLY + 1 )) | cut -d' ' -f2- \
            | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
    fi

    if [ "$DOM" -eq 1 ]; then
        FILES_MONTHLY="${BACKUP_DIR}/files/kaasb-files-monthly-$(date -u '+%Y-%m').tar.gz"
        cp "${FILES_OUTFILE}" "${FILES_MONTHLY}"
        sha256sum "${FILES_MONTHLY}" > "${FILES_MONTHLY%.tar.gz}.sha256"
        log "Monthly files backup: $(basename "${FILES_MONTHLY}")"
        s3_upload "${FILES_MONTHLY}" "monthly/files"
        find "${BACKUP_DIR}/files" -name "kaasb-files-monthly-*.tar.gz" -printf '%T@ %p\n' \
            | sort -rn | tail -n +$(( KEEP_MONTHLY + 1 )) | cut -d' ' -f2- \
            | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
    fi

    # Rotate daily files backups
    find "${BACKUP_DIR}/files" -name "kaasb-files-daily-*.tar.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_DAILY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true

    FILES_FINAL=$(encrypt_if_configured "${FILES_OUTFILE}")
    s3_upload "${FILES_FINAL}" "daily/files"
    record_metadata "files-daily" "${FILES_FINAL}" "${FILES_FILE_SIZE}" "upload_files"
else
    log "Files backup skipped (no data or volume not found)"
fi

# ---------------------------------------------------------------------------
# 3. CONFIGURATION BACKUP
# ---------------------------------------------------------------------------
log "[3/3] Configuration backup..."

CONFIGS_OUTFILE="${BACKUP_DIR}/configs/kaasb-configs-daily-${TIMESTAMP}.tar.gz"
TMPDIR_CONF=$(mktemp -d)

# Collect config files into a staging directory
mkdir -p "${TMPDIR_CONF}/kaasb-configs"

# .env.production (contains secrets — MUST be encrypted if GPG key is set)
cp "${ENV_FILE}" "${TMPDIR_CONF}/kaasb-configs/.env.production" 2>/dev/null || true

# Docker Compose files
cp "${DEPLOY_DIR}/docker-compose.prod.yml" "${TMPDIR_CONF}/kaasb-configs/" 2>/dev/null || true
cp "${DEPLOY_DIR}/docker-compose.monitoring.yml" "${TMPDIR_CONF}/kaasb-configs/" 2>/dev/null || true

# Nginx config
cp "${DEPLOY_DIR}/docker/nginx/nginx.conf" "${TMPDIR_CONF}/kaasb-configs/nginx.conf" 2>/dev/null || true

# PostgreSQL config
cp "${DEPLOY_DIR}/docker/postgres/postgresql.conf" \
    "${TMPDIR_CONF}/kaasb-configs/postgresql.conf" 2>/dev/null || true

# Alertmanager config (may contain webhook secrets)
cp "${DEPLOY_DIR}/docker/alertmanager/alertmanager.yml" \
    "${TMPDIR_CONF}/kaasb-configs/alertmanager.yml" 2>/dev/null || true

# SSL certificates from Let's Encrypt Docker volume
docker run --rm \
    -v kaasb_letsencrypt:/letsencrypt:ro \
    -v "${TMPDIR_CONF}/kaasb-configs":/backup \
    alpine:3.19 \
    sh -c "[ -d /letsencrypt/live ] && tar czf /backup/ssl-certs.tar.gz -C /letsencrypt . || echo 'no certs'" \
    2>/dev/null || true

# Deploy script and cron
cp "${DEPLOY_DIR}/deploy.sh" "${TMPDIR_CONF}/kaasb-configs/" 2>/dev/null || true
[ -f "/etc/cron.d/kaasb" ] && cp /etc/cron.d/kaasb "${TMPDIR_CONF}/kaasb-configs/cron-kaasb" 2>/dev/null || true

# Package everything
tar czf "${CONFIGS_OUTFILE}" -C "${TMPDIR_CONF}" kaasb-configs/
rm -rf "${TMPDIR_CONF}"

CONFIGS_SIZE=$(du -sh "${CONFIGS_OUTFILE}" | cut -f1)
log "Configs backup: ${CONFIGS_SIZE} → $(basename "${CONFIGS_OUTFILE}")"

if ! gzip -t "${CONFIGS_OUTFILE}" 2>/dev/null; then
    warn "Configs backup gzip check failed"
fi

sha256sum "${CONFIGS_OUTFILE}" > "${CONFIGS_OUTFILE%.tar.gz}.sha256"
CONFIGS_FILE_SIZE=$(stat -c %s "${CONFIGS_OUTFILE}" 2>/dev/null || echo 0)

# Weekly + monthly copies
if [ "$DOW" -eq 7 ]; then
    CONFIGS_WEEKLY="${BACKUP_DIR}/configs/kaasb-configs-weekly-$(date -u '+%Y-W%V').tar.gz"
    cp "${CONFIGS_OUTFILE}" "${CONFIGS_WEEKLY}"
    sha256sum "${CONFIGS_WEEKLY}" > "${CONFIGS_WEEKLY%.tar.gz}.sha256"
    log "Weekly configs backup: $(basename "${CONFIGS_WEEKLY}")"
    s3_upload "${CONFIGS_WEEKLY}" "weekly/configs"
    find "${BACKUP_DIR}/configs" -name "kaasb-configs-weekly-*.tar.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_WEEKLY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
fi

if [ "$DOM" -eq 1 ]; then
    CONFIGS_MONTHLY="${BACKUP_DIR}/configs/kaasb-configs-monthly-$(date -u '+%Y-%m').tar.gz"
    cp "${CONFIGS_OUTFILE}" "${CONFIGS_MONTHLY}"
    sha256sum "${CONFIGS_MONTHLY}" > "${CONFIGS_MONTHLY%.tar.gz}.sha256"
    log "Monthly configs backup: $(basename "${CONFIGS_MONTHLY}")"
    s3_upload "${CONFIGS_MONTHLY}" "monthly/configs"
    find "${BACKUP_DIR}/configs" -name "kaasb-configs-monthly-*.tar.gz" -printf '%T@ %p\n' \
        | sort -rn | tail -n +$(( KEEP_MONTHLY + 1 )) | cut -d' ' -f2- \
        | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true
fi

# Rotate daily config backups
find "${BACKUP_DIR}/configs" -name "kaasb-configs-daily-*.tar.gz" -printf '%T@ %p\n' \
    | sort -rn | tail -n +$(( KEEP_DAILY + 1 )) | cut -d' ' -f2- \
    | xargs -r rm -vf >> "$LOG_FILE" 2>&1 || true

CONFIGS_FINAL=$(encrypt_if_configured "${CONFIGS_OUTFILE}")
s3_upload "${CONFIGS_FINAL}" "daily/configs"
record_metadata "configs-daily" "${CONFIGS_FINAL}" "${CONFIGS_FILE_SIZE}" "env+nginx+certs"

# ---------------------------------------------------------------------------
# Disk space check
# ---------------------------------------------------------------------------
DISK_USED=$(df -h "${BACKUP_DIR}" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "${DISK_USED:-0}" -gt 80 ]; then
    warn "Disk usage ${DISK_USED}% — consider pruning backups or expanding storage"
fi

# ---------------------------------------------------------------------------
# Prometheus textfile collector metric
# node_exporter scrapes /var/lib/node_exporter/textfile/*.prom and exposes
# them on /metrics. The BackupTooOld alert rule evaluates this gauge.
# Writes are atomic (tmp + mv) so node_exporter never reads a half-written file.
# ---------------------------------------------------------------------------
METRIC_DIR="/var/lib/node_exporter/textfile"
if [ -d "${METRIC_DIR}" ]; then
    METRIC_TMP=$(mktemp "${METRIC_DIR}/.kaasb_backup.prom.XXXXXX") || METRIC_TMP=""
    if [ -n "${METRIC_TMP}" ]; then
        cat > "${METRIC_TMP}" <<EOF
# HELP kaasb_last_backup_timestamp_seconds Unix epoch of last successful Kaasb backup run
# TYPE kaasb_last_backup_timestamp_seconds gauge
kaasb_last_backup_timestamp_seconds $(date +%s)
EOF
        chmod 644 "${METRIC_TMP}"
        mv -f "${METRIC_TMP}" "${METRIC_DIR}/kaasb_backup.prom"
    else
        warn "Could not write Prometheus metric to ${METRIC_DIR} — BackupTooOld alert will not fire"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "========================================================"
log "  Backup job finished successfully — ${TIMESTAMP}"
log "  DB:      $(basename "${DB_FINAL}") (${DB_SIZE})"
[ -n "${FILES_OUTFILE:-}" ] && \
log "  Files:   $(basename "${FILES_FINAL:-none}") (${FILES_SIZE:-0})"
log "  Configs: $(basename "${CONFIGS_FINAL}") (${CONFIGS_SIZE})"
log "  Disk:    ${DISK_USED}% used"
log "========================================================"
