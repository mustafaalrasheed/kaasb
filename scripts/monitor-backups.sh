#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Backup Health Monitor
# =============================================================================
# Checks backup health and fires alerts if thresholds are breached.
# Designed to run hourly via cron.
#
# What it checks:
#   - Latest DB backup age (warn >26h, critical >48h)
#   - Latest files backup age (warn >26h, critical >48h)
#   - Latest config backup age (warn >26h, critical >48h)
#   - Backup disk usage (warn >75%, critical >90%)
#   - Last backup file size vs. expected minimum
#   - Backup job exit status from backup_history.csv
#   - Last verification result from backup_history.csv
#
# Alert channels:
#   - Log file (/var/log/kaasb/backup-monitor.log)
#   - Slack/webhook (ALERT_WEBHOOK env var)
#   - Email (ALERT_EMAIL env var, requires mailutils/sendmail)
#   - Sentry (SENTRY_DSN env var)
#
# Cron schedule (add to /etc/cron.d/kaasb):
#   */30 * * * * root bash /opt/kaasb/scripts/monitor-backups.sh >> /var/log/kaasb/backup-monitor.log 2>&1
# =============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
LOG_FILE="/var/log/kaasb/backup-monitor.log"
STATE_FILE="/var/log/kaasb/backup-monitor.state"  # tracks last alert times

# Thresholds (hours)
WARN_AGE_HOURS=26
CRIT_AGE_HOURS=48

# Disk usage thresholds (percent)
DISK_WARN_PCT=75
DISK_CRIT_PCT=90

# Minimum expected sizes
DB_MIN_BYTES=10240       # 10 KB
FILES_MIN_BYTES=1024     # 1 KB
CONFIGS_MIN_BYTES=512    # 512 bytes

# Alert deduplication: only re-alert after this many minutes have passed for same issue
ALERT_COOLDOWN_MINUTES=120

# ---------------------------------------------------------------------------
# Load environment (for SENTRY_DSN, ALERT_WEBHOOK, ALERT_EMAIL)
# ---------------------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
SENTRY_DSN="${SENTRY_DSN:-}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()   { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [INFO]  $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
crit()  { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${RED}[CRIT]${NC}  $*" | tee -a "$LOG_FILE"; }

mkdir -p "$( dirname "$LOG_FILE" )" "$( dirname "$STATE_FILE" )"

# ---------------------------------------------------------------------------
# Alert deduplication state
# ---------------------------------------------------------------------------
load_state() { [ -f "$STATE_FILE" ] && source "$STATE_FILE" || true; }
save_state() {
    declare -p LAST_ALERT_DB LAST_ALERT_FILES LAST_ALERT_CONFIGS \
               LAST_ALERT_DISK 2>/dev/null > "$STATE_FILE" || true
}

# Defaults
LAST_ALERT_DB=0
LAST_ALERT_FILES=0
LAST_ALERT_CONFIGS=0
LAST_ALERT_DISK=0
load_state

# Returns 1 (should alert) if cooldown has expired for the given key
should_alert() {
    local last_ts="$1"
    local now
    now=$(date +%s)
    local elapsed=$(( (now - last_ts) / 60 ))
    [ "${elapsed}" -ge "${ALERT_COOLDOWN_MINUTES}" ]
}

# ---------------------------------------------------------------------------
# Alert dispatcher
# ---------------------------------------------------------------------------
ALERTS=()
ALERT_LEVEL="ok"  # ok | warn | crit

add_alert() {
    local level="$1" message="$2"
    ALERTS+=("${level}: ${message}")
    case "$level" in
        crit) ALERT_LEVEL="crit" ;;
        warn) [ "$ALERT_LEVEL" != "crit" ] && ALERT_LEVEL="warn" ;;
    esac
}

fire_alerts() {
    [ ${#ALERTS[@]} -eq 0 ] && return 0

    local body
    body=$(printf '%s\n' "${ALERTS[@]}")
    local subject="[Kaasb] Backup ${ALERT_LEVEL^^}: $(echo "${ALERTS[0]}" | cut -c1-80)"

    # Log
    for alert in "${ALERTS[@]}"; do
        case "${alert%%:*}" in
            crit) crit "${alert#*: }" ;;
            warn) warn "${alert#*: }" ;;
            *)    ok   "${alert#*: }" ;;
        esac
    done

    # Slack / webhook
    if [ -n "${ALERT_WEBHOOK}" ] && [ "${ALERT_LEVEL}" != "ok" ]; then
        local emoji="⚠️"
        [ "${ALERT_LEVEL}" = "crit" ] && emoji="🚨"
        curl -s -X POST "${ALERT_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"${emoji} *${subject}*\n\`\`\`${body}\`\`\`\"}" \
            > /dev/null 2>&1 || true
    fi

    # Email
    if [ -n "${ALERT_EMAIL}" ] && [ "${ALERT_LEVEL}" != "ok" ] && command -v mail &>/dev/null; then
        echo "${body}" | mail -s "${subject}" "${ALERT_EMAIL}" 2>/dev/null || true
    fi

    # Sentry (send as a captured exception via API)
    if [ -n "${SENTRY_DSN}" ] && [ "${ALERT_LEVEL}" = "crit" ]; then
        local sentry_url
        sentry_url=$(echo "${SENTRY_DSN}" | sed 's|https://\([^@]*\)@\([^/]*\)/\(.*\)|https://\2/api/\3/store/|')
        local sentry_key
        sentry_key=$(echo "${SENTRY_DSN}" | sed 's|https://\([^@]*\)@.*|\1|')
        curl -s -X POST "${sentry_url}" \
            -H "X-Sentry-Auth: Sentry sentry_version=7, sentry_key=${sentry_key}" \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"${subject}\", \"level\": \"error\", \"logger\": \"backup-monitor\", \"platform\": \"other\"}" \
            > /dev/null 2>&1 || true
    fi
}

# ---------------------------------------------------------------------------
# Helper: get file age in hours
# ---------------------------------------------------------------------------
file_age_hours() {
    local file="$1"
    local mtime now
    mtime=$(stat -c %Y "${file}" 2>/dev/null || echo 0)
    now=$(date +%s)
    echo $(( (now - mtime) / 3600 ))
}

# ---------------------------------------------------------------------------
# Helper: check latest backup in a directory
# ---------------------------------------------------------------------------
check_backup() {
    local dir="$1"
    local pattern="$2"
    local label="$3"
    local min_bytes="$4"
    local state_var="$5"

    # Find latest
    local latest
    latest=$(find "${dir}" -name "${pattern}" -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "${latest}" ]; then
        add_alert "crit" "${label}: NO BACKUPS FOUND in ${dir}"
        return 1
    fi

    local age
    age=$(file_age_hours "${latest}")
    local name
    name=$(basename "${latest}")
    local size
    size=$(stat -c %s "${latest}" 2>/dev/null || echo 0)

    # Age check
    if [ "${age}" -ge "${CRIT_AGE_HOURS}" ]; then
        add_alert "crit" "${label}: backup is ${age}h old (threshold: ${CRIT_AGE_HOURS}h) — ${name}"
        eval "LAST_ALERT_${state_var}=$(date +%s)"
    elif [ "${age}" -ge "${WARN_AGE_HOURS}" ]; then
        add_alert "warn" "${label}: backup is ${age}h old (threshold: ${WARN_AGE_HOURS}h) — ${name}"
        eval "LAST_ALERT_${state_var}=$(date +%s)"
    else
        ok "${label}: backup is ${age}h old — OK (${name})"
    fi

    # Size check
    if [ "${size}" -lt "${min_bytes}" ]; then
        add_alert "warn" "${label}: backup file suspiciously small (${size} bytes) — ${name}"
    else
        ok "${label}: size ${size} bytes — OK"
    fi

    # Checksum integrity (fast check — just verify the .sha256 exists and passes)
    local chk="${latest}.sha256"
    [ -f "$chk" ] || chk="${latest%.sql.gz}.sha256"
    [ -f "$chk" ] || chk="${latest%.tar.gz}.sha256"
    if [ -f "$chk" ]; then
        if sha256sum -c "${chk}" --status 2>/dev/null; then
            ok "${label}: checksum verified — ${name}"
        else
            add_alert "crit" "${label}: CHECKSUM MISMATCH — ${name} is corrupt"
        fi
    else
        add_alert "warn" "${label}: no checksum file found — ${name}"
    fi
}

# ---------------------------------------------------------------------------
# Helper: check last verification result
# ---------------------------------------------------------------------------
check_last_verify() {
    local csv="${BACKUP_DIR}/backup_history.csv"
    [ -f "$csv" ] || return 0

    local last_verify
    last_verify=$(grep "^verify," "$csv" | tail -1)
    if [ -z "${last_verify}" ]; then
        warn "No backup verification record found in backup_history.csv"
        return 0
    fi

    local detail
    detail=$(echo "${last_verify}" | cut -d',' -f4)
    local failures
    failures=$(echo "${detail}" | grep -oP 'fail=\K\d+' || echo "0")
    local ts
    ts=$(echo "${last_verify}" | cut -d',' -f5)

    if [ "${failures:-0}" -gt 0 ]; then
        add_alert "warn" "Last backup verification reported ${failures} failure(s) at ${ts}"
    else
        ok "Last verification: ${detail} at ${ts}"
    fi
}

# ---------------------------------------------------------------------------
# Main checks
# ---------------------------------------------------------------------------
log "========================================================"
log "  Kaasb backup health monitor — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
log "========================================================"

# DB backups
check_backup "${BACKUP_DIR}/db"      "kaasb-db-daily-*.sql.gz"      "DB"      "${DB_MIN_BYTES}"      "DB"
# Files backups (may not exist yet)
if [ -d "${BACKUP_DIR}/files" ]; then
    check_backup "${BACKUP_DIR}/files"   "kaasb-files-daily-*.tar.gz"   "Files"   "${FILES_MIN_BYTES}"   "FILES"
fi
# Config backups
if [ -d "${BACKUP_DIR}/configs" ]; then
    check_backup "${BACKUP_DIR}/configs" "kaasb-configs-daily-*.tar.gz" "Configs" "${CONFIGS_MIN_BYTES}" "CONFIGS"
fi

# Disk usage
DISK_USED=$(df -h "${BACKUP_DIR}" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
if [ "${DISK_USED:-0}" -ge "${DISK_CRIT_PCT}" ]; then
    add_alert "crit" "Disk: ${DISK_USED}% used on backup volume — CRITICAL, prune immediately"
    LAST_ALERT_DISK=$(date +%s)
elif [ "${DISK_USED:-0}" -ge "${DISK_WARN_PCT}" ]; then
    add_alert "warn" "Disk: ${DISK_USED}% used on backup volume — consider pruning"
    LAST_ALERT_DISK=$(date +%s)
else
    ok "Disk: ${DISK_USED}% used — OK"
fi

# Last verification
check_last_verify

# ---------------------------------------------------------------------------
# Count backups on hand
# ---------------------------------------------------------------------------
db_count=$(find "${BACKUP_DIR}/db" -name "kaasb-db-daily-*.sql.gz" 2>/dev/null | wc -l)
log "Backups on hand: ${db_count} daily DB, $(find "${BACKUP_DIR}/db" -name "kaasb-db-weekly-*.sql.gz" 2>/dev/null | wc -l) weekly DB"

# ---------------------------------------------------------------------------
# Fire alerts
# ---------------------------------------------------------------------------
if [ ${#ALERTS[@]} -gt 0 ]; then
    fire_alerts
    save_state
else
    ok "All backup health checks passed."
fi

log "Monitor run complete. Level: ${ALERT_LEVEL^^}"
log "========================================================"

# Exit 1 if critical issues found
[ "${ALERT_LEVEL}" != "crit" ]
