#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Backup Verification Script
# =============================================================================
# Performs comprehensive integrity checks on all recent backups:
#   1. Gzip integrity test on every backup file
#   2. SHA-256 checksum verification
#   3. SQL structure validation (header + table count)
#   4. Live restore test: restores DB to a temporary container and queries it
#   5. Files backup: spot-checks tar listing
#   6. Config backup: spot-checks tar listing for required files
#
# Designed to run monthly (or on-demand before a restore).
#
# Cron schedule (add to /etc/cron.d/kaasb):
#   0 4 1 * * root bash /opt/kaasb/scripts/backup-verify.sh >> /var/log/kaasb/backup-verify.log 2>&1
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more failures
# =============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
LOG_FILE="/var/log/kaasb/backup-verify.log"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.prod.yml --env-file ${ENV_FILE}"

# Temporary container name for restore test
VERIFY_CONTAINER="kaasb_verify_$$"
VERIFY_DB="kaasb_verify"

# Slack/webhook alerting (leave empty to skip)
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
PASS=0
FAIL=0
WARN=0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()     { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [INFO]  $*" | tee -a "$LOG_FILE"; }
pass()    { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${GREEN}[PASS]${NC}  $*" | tee -a "$LOG_FILE"; (( PASS++ )); }
fail()    { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${RED}[FAIL]${NC}  $*" | tee -a "$LOG_FILE"; (( FAIL++ )); }
warn_chk(){ echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; (( WARN++ )); }

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found"; exit 1; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

mkdir -p "$( dirname "$LOG_FILE" )"

log "========================================================"
log "  Kaasb backup verification started"
log "========================================================"

TIMESTAMP=$(date -u '+%Y%m%d-%H%M%S')
OVERALL_STATUS=0

# ---------------------------------------------------------------------------
# Helper: verify a single backup file
# ---------------------------------------------------------------------------
verify_file() {
    local file="$1"
    local label="$2"
    local name
    name="$(basename "${file}")"

    # 1. File exists and is not empty
    if [ ! -f "${file}" ]; then
        fail "${label}: file not found — ${name}"; return 1
    fi
    if [ ! -s "${file}" ]; then
        fail "${label}: file is empty — ${name}"; return 1
    fi

    # 2. Gzip integrity
    if gzip -t "${file}" 2>/dev/null; then
        pass "${label}: gzip integrity OK — ${name}"
    else
        fail "${label}: gzip integrity FAILED — ${name}"; return 1
    fi

    # 3. Checksum
    local chk="${file}.sha256"
    [ -f "$chk" ] || chk="${file%.sql.gz}.sha256"
    [ -f "$chk" ] || chk="${file%.tar.gz}.sha256"

    if [ -f "$chk" ]; then
        if sha256sum -c "${chk}" --status 2>/dev/null; then
            pass "${label}: SHA-256 checksum OK — ${name}"
        else
            fail "${label}: SHA-256 checksum MISMATCH — ${name}"; return 1
        fi
    else
        warn_chk "${label}: no checksum file found — ${name}"
    fi

    # 4. Size check
    local size
    size=$(stat -c %s "${file}" 2>/dev/null || echo 0)
    if [ "${size}" -lt 1024 ]; then
        warn_chk "${label}: file is suspiciously small (${size} bytes) — ${name}"
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Helper: verify SQL structure of a DB backup
# ---------------------------------------------------------------------------
verify_sql_structure() {
    local file="$1"
    local name
    name="$(basename "${file}")"

    local header
    header=$(zcat "${file}" 2>/dev/null | head -1)
    if [[ "${header}" == *"PostgreSQL database dump"* ]]; then
        pass "DB structure: valid pg_dump header — ${name}"
    else
        fail "DB structure: invalid header '${header}' — ${name}"; return 1
    fi

    local table_count
    table_count=$(zcat "${file}" 2>/dev/null | grep -c "^CREATE TABLE" || true)
    if [ "${table_count:-0}" -gt 0 ]; then
        pass "DB structure: ${table_count} CREATE TABLE statements — ${name}"
    else
        fail "DB structure: no CREATE TABLE statements — ${name}"; return 1
    fi
}

# ---------------------------------------------------------------------------
# Helper: live restore test in a temporary PostgreSQL container
# ---------------------------------------------------------------------------
live_restore_test() {
    local file="$1"
    local name
    name="$(basename "${file}")"

    log "Live restore test: ${name}"

    # Pull the same postgres image used in production
    docker pull postgres:16-alpine -q 2>/dev/null || true

    # Start a temp container
    docker run -d \
        --name "${VERIFY_CONTAINER}" \
        -e POSTGRES_USER="${DB_USER}" \
        -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
        -e POSTGRES_DB="${VERIFY_DB}" \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        postgres:16-alpine > /dev/null 2>&1

    # Wait for it to be ready
    local ready=0
    for i in $(seq 1 20); do
        if docker exec "${VERIFY_CONTAINER}" pg_isready -U "${DB_USER}" -d "${VERIFY_DB}" \
            > /dev/null 2>&1; then
            ready=1; break
        fi
        sleep 2
    done

    if [ "${ready}" -eq 0 ]; then
        fail "Live restore: temp container did not start in time"
        docker rm -f "${VERIFY_CONTAINER}" > /dev/null 2>&1 || true
        return 1
    fi

    # Stream backup into temp DB
    if gunzip -c "${file}" \
        | docker exec -i "${VERIFY_CONTAINER}" \
            psql -U "${DB_USER}" -d "${VERIFY_DB}" -v ON_ERROR_STOP=1 \
            > /dev/null 2>&1; then
        pass "Live restore: pg_restore into temp container — ${name}"
    else
        fail "Live restore: pg_restore FAILED — ${name}"
        docker rm -f "${VERIFY_CONTAINER}" > /dev/null 2>&1 || true
        return 1
    fi

    # Verify table count
    local restored_tables
    restored_tables=$(docker exec "${VERIFY_CONTAINER}" \
        psql -U "${DB_USER}" -d "${VERIFY_DB}" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" \
        2>/dev/null | xargs)

    if [ "${restored_tables:-0}" -gt 0 ]; then
        pass "Live restore: ${restored_tables} tables verified in temp DB — ${name}"
    else
        fail "Live restore: no tables found after restore — ${name}"
    fi

    # Verify row counts on key tables
    for tbl in users jobs contracts transactions; do
        local rows
        rows=$(docker exec "${VERIFY_CONTAINER}" \
            psql -U "${DB_USER}" -d "${VERIFY_DB}" -t -c \
            "SELECT COUNT(*) FROM ${tbl};" 2>/dev/null | xargs || echo "N/A")
        log "  ${tbl}: ${rows} rows"
    done

    # Clean up
    docker rm -f "${VERIFY_CONTAINER}" > /dev/null 2>&1 || true
    pass "Live restore: temp container cleaned up"
}

# ---------------------------------------------------------------------------
# Helper: verify tar.gz listing
# ---------------------------------------------------------------------------
verify_tar_contents() {
    local file="$1"
    local label="$2"
    local required_pattern="$3"  # grep pattern that must appear in listing

    local listing
    listing=$(tar tzf "${file}" 2>/dev/null) || { fail "${label}: cannot read tar listing — $(basename "${file}")"; return 1; }

    if echo "${listing}" | grep -q "${required_pattern}"; then
        pass "${label}: required content found ('${required_pattern}') — $(basename "${file}")"
    else
        fail "${label}: required content '${required_pattern}' NOT found in tar — $(basename "${file}")"
        return 1
    fi

    local file_count
    file_count=$(echo "${listing}" | wc -l)
    log "  ${label}: ${file_count} entries in archive"
}

# ---------------------------------------------------------------------------
# Check backup age — warn if latest backup is older than 26 hours
# ---------------------------------------------------------------------------
check_backup_age() {
    local dir="$1" pattern="$2" label="$3"
    local latest
    latest=$(find "${dir}" -name "${pattern}" -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "${latest}" ]; then
        fail "${label}: no backups found in ${dir}"
        return 1
    fi

    local mtime
    mtime=$(stat -c %Y "${latest}" 2>/dev/null || echo 0)
    local now
    now=$(date +%s)
    local age_hours=$(( (now - mtime) / 3600 ))

    if [ "${age_hours}" -le 26 ]; then
        pass "${label}: latest backup is ${age_hours}h old — $(basename "${latest}")"
    elif [ "${age_hours}" -le 48 ]; then
        warn_chk "${label}: latest backup is ${age_hours}h old (> 26h) — $(basename "${latest}")"
    else
        fail "${label}: latest backup is ${age_hours}h old (> 48h) — no recent backup!"
    fi

    echo "${latest}"
}

# ---------------------------------------------------------------------------
# Run checks
# ---------------------------------------------------------------------------

# --- Database backups ---
log ""
log "─── DATABASE BACKUPS ─────────────────────────────────────"

LATEST_DB=$(check_backup_age "${BACKUP_DIR}/db" "kaasb-db-daily-*.sql.gz" "DB daily")
if [ -n "${LATEST_DB:-}" ]; then
    verify_file "${LATEST_DB}" "DB daily"
    verify_sql_structure "${LATEST_DB}"
    # Live restore test (the most thorough check)
    live_restore_test "${LATEST_DB}" || OVERALL_STATUS=1
fi

# Check weekly exists if we're past Sunday
if find "${BACKUP_DIR}/db" -name "kaasb-db-weekly-*.sql.gz" | grep -q .; then
    LATEST_WEEKLY=$(find "${BACKUP_DIR}/db" -name "kaasb-db-weekly-*.sql.gz" \
        -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
    verify_file "${LATEST_WEEKLY}" "DB weekly"
fi

# --- Files backups ---
log ""
log "─── USER FILES BACKUPS ───────────────────────────────────"
if find "${BACKUP_DIR}/files" -name "kaasb-files-daily-*.tar.gz" | grep -q . 2>/dev/null; then
    LATEST_FILES=$(check_backup_age "${BACKUP_DIR}/files" "kaasb-files-daily-*.tar.gz" "Files daily")
    if [ -n "${LATEST_FILES:-}" ]; then
        verify_file "${LATEST_FILES}" "Files daily"
        # The tar may be empty if no uploads yet — treat as warning, not failure
        local_count=$(tar tzf "${LATEST_FILES}" 2>/dev/null | wc -l || echo 0)
        if [ "${local_count:-0}" -gt 0 ]; then
            pass "Files daily: ${local_count} entries in archive"
        else
            warn_chk "Files daily: archive is empty (no uploads yet?)"
        fi
    fi
else
    warn_chk "Files: no daily backups found (expected if uploads volume is new)"
fi

# --- Config backups ---
log ""
log "─── CONFIG BACKUPS ───────────────────────────────────────"
if find "${BACKUP_DIR}/configs" -name "kaasb-configs-daily-*.tar.gz" | grep -q . 2>/dev/null; then
    LATEST_CONF=$(check_backup_age "${BACKUP_DIR}/configs" "kaasb-configs-daily-*.tar.gz" "Configs daily")
    if [ -n "${LATEST_CONF:-}" ]; then
        verify_file "${LATEST_CONF}" "Configs daily"
        verify_tar_contents "${LATEST_CONF}" "Configs" ".env.production"
        verify_tar_contents "${LATEST_CONF}" "Configs" "nginx.conf"
    fi
else
    fail "Configs: no daily backups found"
    OVERALL_STATUS=1
fi

# --- Disk space ---
log ""
log "─── DISK SPACE ───────────────────────────────────────────"
DISK_USED=$(df -h "${BACKUP_DIR}" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "${DISK_USED:-0}" -lt 70 ]; then
    pass "Disk: ${DISK_USED}% used — healthy"
elif [ "${DISK_USED:-0}" -lt 85 ]; then
    warn_chk "Disk: ${DISK_USED}% used — consider pruning"
else
    fail "Disk: ${DISK_USED}% used — critical, prune immediately"
    OVERALL_STATUS=1
fi

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
echo ""
log "========================================================"
log "  Verification complete: ${PASS} passed, ${WARN} warnings, ${FAIL} failed"
log "========================================================"

# Alert via webhook if failures
if [ "${FAIL}" -gt 0 ] && [ -n "${ALERT_WEBHOOK}" ]; then
    curl -s -X POST "${ALERT_WEBHOOK}" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"[Kaasb] Backup verification FAILED: ${FAIL} failures, ${WARN} warnings. Check /var/log/kaasb/backup-verify.log\"}" \
        > /dev/null 2>&1 || true
    log "Alert sent to webhook."
fi

# Write result to metadata CSV
METADATA_LOG="${BACKUP_DIR}/backup_history.csv"
if [ ! -f "$METADATA_LOG" ]; then
    echo "backup_type,file_name,file_size_bytes,detail,completed_at" > "$METADATA_LOG"
fi
echo "verify,verify-${TIMESTAMP},0,pass=${PASS} warn=${WARN} fail=${FAIL},$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    >> "$METADATA_LOG"

[ "${FAIL}" -eq 0 ] || { OVERALL_STATUS=1; }
exit ${OVERALL_STATUS}
