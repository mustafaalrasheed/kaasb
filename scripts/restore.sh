#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Full System Restore Script
# =============================================================================
# Restores any combination of: database, user files, and/or config files.
# Supports --dry-run to preview all actions without making changes.
#
# Usage:
#   bash restore.sh [OPTIONS]
#
# Options:
#   --db     <file.sql.gz>     Restore database from this backup file
#   --files  <file.tar.gz>     Restore user uploads from this backup file
#   --config <file.tar.gz>     Restore configuration files from this backup
#   --all                      Restore all three from the latest backups
#   --dry-run                  Print every action that would be taken; do nothing
#   --no-safety-backup         Skip pre-restore DB snapshot (faster, riskier)
#   --help                     Show this help
#
# Examples:
#   # Full restore from latest backups (interactive confirmation)
#   bash restore.sh --all
#
#   # Dry-run to preview what --all would do
#   bash restore.sh --all --dry-run
#
#   # Restore only the database
#   bash restore.sh --db /opt/kaasb/backups/db/kaasb-db-daily-20260327-020001.sql.gz
#
#   # Restore files from a specific backup with dry-run
#   bash restore.sh --files /opt/kaasb/backups/files/kaasb-files-daily-20260327-020010.tar.gz --dry-run
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
LOG_FILE="/var/log/kaasb/restore.log"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.prod.yml --env-file ${ENV_FILE}"

# ---------------------------------------------------------------------------
# Colours and logging
# ---------------------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()   { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${GREEN}[RESTORE]${NC} $*" | tee -a "$LOG_FILE"; }
info()  { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${CYAN}[INFO]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${YELLOW}[WARN]${NC}    $*" | tee -a "$LOG_FILE"; }
error() { echo -e "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${RED}[ERROR]${NC}   $*" | tee -a "$LOG_FILE" >&2; exit 1; }

dry_log() {
    echo -e "${CYAN}[DRY-RUN]${NC} Would execute: $*"
}

# Execute a command, or just print it in dry-run mode
run() {
    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "$*"
    else
        eval "$@"
    fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DRY_RUN="false"
SAFETY_BACKUP="true"
DO_DB="false"
DO_FILES="false"
DO_CONFIG="false"
DB_FILE=""
FILES_FILE=""
CONFIG_FILE=""

show_help() {
    grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -35
    exit 0
}

[ $# -eq 0 ] && show_help

while [ $# -gt 0 ]; do
    case "$1" in
        --db)      DO_DB="true";     DB_FILE="$2";     shift 2 ;;
        --files)   DO_FILES="true";  FILES_FILE="$2";  shift 2 ;;
        --config)  DO_CONFIG="true"; CONFIG_FILE="$2"; shift 2 ;;
        --all)     DO_DB="true"; DO_FILES="true"; DO_CONFIG="true"; shift ;;
        --dry-run) DRY_RUN="true"; shift ;;
        --no-safety-backup) SAFETY_BACKUP="false"; shift ;;
        --help|-h) show_help ;;
        *) error "Unknown option: $1" ;;
    esac
done

if [ "${DO_DB}" = "false" ] && [ "${DO_FILES}" = "false" ] && [ "${DO_CONFIG}" = "false" ]; then
    error "No restore targets specified. Use --db, --files, --config, or --all"
fi

mkdir -p "$( dirname "$LOG_FILE" )"

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || error "$ENV_FILE not found"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
[ -n "${DB_USER:-}" ]  || error "DB_USER not set"
[ -n "${DB_NAME:-}" ]  || error "DB_NAME not set"

# ---------------------------------------------------------------------------
# Helper: find latest backup matching a pattern
# ---------------------------------------------------------------------------
find_latest() {
    local dir="$1" pattern="$2"
    find "${dir}" -name "${pattern}" -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -1 | cut -d' ' -f2-
}

# ---------------------------------------------------------------------------
# Helper: verify checksum before restoring
# ---------------------------------------------------------------------------
verify_checksum() {
    local file="$1"
    # Checksum file may be <file>.sha256 or <file-without-extension>.sha256
    local chk="${file}.sha256"
    [ -f "$chk" ] || chk="${file%.sql.gz}.sha256"
    [ -f "$chk" ] || chk="${file%.tar.gz}.sha256"

    if [ -f "$chk" ]; then
        info "Verifying checksum: $(basename "${chk}")"
        if sha256sum -c "${chk}" --status 2>/dev/null; then
            log "Checksum OK: $(basename "${file}")"
        else
            error "Checksum MISMATCH for $(basename "${file}") — backup may be corrupt. Aborting."
        fi
    else
        warn "No checksum file found for $(basename "${file}") — skipping verification"
    fi
}

# ---------------------------------------------------------------------------
# Helper: decrypt GPG file if needed
# ---------------------------------------------------------------------------
decrypt_if_needed() {
    local file="$1"
    if [[ "$file" == *.gpg ]]; then
        local decrypted="${file%.gpg}"
        info "Decrypting: $(basename "${file}")"
        if [ "${DRY_RUN}" = "true" ]; then
            dry_log "gpg --batch --output ${decrypted} --decrypt ${file}"
            echo "${decrypted}"
        else
            gpg --batch --output "${decrypted}" --decrypt "${file}"
            echo "${decrypted}"
        fi
    else
        echo "${file}"
    fi
}

# ---------------------------------------------------------------------------
# Resolve --all targets to latest backup files
# ---------------------------------------------------------------------------
if [ "${DO_DB}" = "true" ] && [ -z "${DB_FILE}" ]; then
    DB_FILE=$(find_latest "${BACKUP_DIR}/db" "kaasb-db-daily-*.sql.gz")
    [ -n "${DB_FILE}" ] || error "No daily DB backup found in ${BACKUP_DIR}/db"
    info "Latest DB backup: $(basename "${DB_FILE}")"
fi

if [ "${DO_FILES}" = "true" ] && [ -z "${FILES_FILE}" ]; then
    FILES_FILE=$(find_latest "${BACKUP_DIR}/files" "kaasb-files-daily-*.tar.gz")
    if [ -z "${FILES_FILE}" ]; then
        warn "No files backup found — skipping file restore"
        DO_FILES="false"
    else
        info "Latest files backup: $(basename "${FILES_FILE}")"
    fi
fi

if [ "${DO_CONFIG}" = "true" ] && [ -z "${CONFIG_FILE}" ]; then
    CONFIG_FILE=$(find_latest "${BACKUP_DIR}/configs" "kaasb-configs-daily-*.tar.gz")
    if [ -z "${CONFIG_FILE}" ]; then
        warn "No config backup found — skipping config restore"
        DO_CONFIG="false"
    else
        info "Latest config backup: $(basename "${CONFIG_FILE}")"
    fi
fi

# ---------------------------------------------------------------------------
# Summary and confirmation
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║             KAASB PLATFORM — RESTORE SUMMARY                ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
[ "${DRY_RUN}" = "true" ] && \
    echo -e "${CYAN}  MODE: DRY-RUN — no changes will be made${NC}"
echo ""
[ "${DO_DB}" = "true" ]     && echo -e "  Database : ${GREEN}$(basename "${DB_FILE}")${NC}"
[ "${DO_FILES}" = "true" ]  && echo -e "  Files    : ${GREEN}$(basename "${FILES_FILE}")${NC}"
[ "${DO_CONFIG}" = "true" ] && echo -e "  Configs  : ${GREEN}$(basename "${CONFIG_FILE}")${NC}"
echo ""

if [ "${DRY_RUN}" = "false" ]; then
    echo -e "${RED}  ⚠  WARNING: This operation is DESTRUCTIVE and cannot be undone.${NC}"
    echo -e "${RED}  ⚠  ALL current data in the selected components will be overwritten.${NC}"
    echo ""
    read -rp "  Type 'restore' to confirm: " CONFIRM
    [ "$CONFIRM" = "restore" ] || { log "Aborted by user."; exit 0; }
    echo ""
fi

TIMESTAMP=$(date -u '+%Y%m%d-%H%M%S')
log "Restore started — ${TIMESTAMP}"

# ---------------------------------------------------------------------------
# STEP 1: Pre-restore safety backup
# ---------------------------------------------------------------------------
if [ "${DO_DB}" = "true" ] && [ "${SAFETY_BACKUP}" = "true" ]; then
    log "Creating pre-restore safety snapshot..."
    SAFETY="${BACKUP_DIR}/db/kaasb-db-pre-restore-${TIMESTAMP}.sql.gz"
    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "$COMPOSE exec -T db pg_dump -U ${DB_USER} ${DB_NAME} | gzip -9 > ${SAFETY}"
    else
        $COMPOSE exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip -9 > "${SAFETY}" \
            && log "Safety snapshot: $(basename "${SAFETY}")" \
            || warn "Safety snapshot failed (database may not be running)"
    fi
fi

# ---------------------------------------------------------------------------
# STEP 2: Database restore
# ---------------------------------------------------------------------------
if [ "${DO_DB}" = "true" ]; then
    log "─── DATABASE RESTORE ────────────────────────────────────"

    [ -f "${DB_FILE}" ] || error "DB backup file not found: ${DB_FILE}"
    verify_checksum "${DB_FILE}"

    ACTUAL_DB_FILE=$(decrypt_if_needed "${DB_FILE}")

    # Validate gzip integrity
    if [ "${DRY_RUN}" = "false" ]; then
        gzip -t "${ACTUAL_DB_FILE}" 2>/dev/null || error "DB backup gzip integrity check failed"
        log "Gzip integrity: OK"
    else
        dry_log "gzip -t ${ACTUAL_DB_FILE}"
    fi

    # Stop application containers (keep DB running)
    log "Stopping application containers..."
    run "$COMPOSE stop backend frontend nginx 2>/dev/null || true"

    # Terminate existing connections, drop and recreate database
    log "Recreating database '${DB_NAME}'..."
    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "Terminate all connections to ${DB_NAME}"
        dry_log "DROP DATABASE ${DB_NAME}"
        dry_log "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}"
    else
        $COMPOSE exec -T db psql -U "${DB_USER}" -d postgres << SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "${DB_NAME}";
CREATE DATABASE "${DB_NAME}" OWNER "${DB_USER}";
GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO "${DB_USER}";
SQL
    fi

    # Stream backup into database
    log "Streaming backup into database..."
    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "gunzip -c ${ACTUAL_DB_FILE} | psql -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=1"
    else
        gunzip -c "${ACTUAL_DB_FILE}" \
            | $COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1
    fi

    # Verify restore
    if [ "${DRY_RUN}" = "false" ]; then
        TABLE_COUNT=$($COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
        log "Tables restored: ${TABLE_COUNT}"
        [ "${TABLE_COUNT:-0}" -gt 0 ] || warn "No tables found — restore may have failed"

        # Row count spot-check
        USER_COUNT=$($COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -t -c \
            "SELECT COUNT(*) FROM users;" 2>/dev/null | xargs || echo "N/A")
        log "Users in restored DB: ${USER_COUNT}"
    fi

    # Run pending migrations
    log "Running migrations on restored database..."
    run "$COMPOSE run --rm backend alembic upgrade head"

    log "Database restore complete."
fi

# ---------------------------------------------------------------------------
# STEP 3: User files restore
# ---------------------------------------------------------------------------
if [ "${DO_FILES}" = "true" ]; then
    log "─── USER FILES RESTORE ──────────────────────────────────"

    [ -f "${FILES_FILE}" ] || error "Files backup not found: ${FILES_FILE}"
    verify_checksum "${FILES_FILE}"

    ACTUAL_FILES_FILE=$(decrypt_if_needed "${FILES_FILE}")

    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "gzip -t ${ACTUAL_FILES_FILE}"
        dry_log "docker run --rm -v kaasb_backend_uploads:/data alpine sh -c 'rm -rf /data/*'"
        dry_log "docker run --rm -v kaasb_backend_uploads:/data -v ${BACKUP_DIR}:/backup alpine tar xzf /backup/... -C /data"
    else
        gzip -t "${ACTUAL_FILES_FILE}" 2>/dev/null || error "Files backup gzip check failed"

        # Clear existing uploads volume
        docker run --rm \
            -v kaasb_backend_uploads:/data \
            alpine:3.19 \
            sh -c 'rm -rf /data/* /data/.* 2>/dev/null || true'

        # Extract backup into volume
        local_filename="$(basename "${ACTUAL_FILES_FILE}")"
        docker run --rm \
            -v kaasb_backend_uploads:/data \
            -v "${BACKUP_DIR}/files":/backup:ro \
            alpine:3.19 \
            tar xzf "/backup/${local_filename}" -C /data
        log "User files restored."
    fi
fi

# ---------------------------------------------------------------------------
# STEP 4: Configuration restore
# ---------------------------------------------------------------------------
if [ "${DO_CONFIG}" = "true" ]; then
    log "─── CONFIGURATION RESTORE ───────────────────────────────"

    [ -f "${CONFIG_FILE}" ] || error "Config backup not found: ${CONFIG_FILE}"
    verify_checksum "${CONFIG_FILE}"

    ACTUAL_CONFIG_FILE=$(decrypt_if_needed "${CONFIG_FILE}")

    if [ "${DRY_RUN}" = "true" ]; then
        dry_log "gzip -t ${ACTUAL_CONFIG_FILE}"
        dry_log "Extract ${ACTUAL_CONFIG_FILE} → ${DEPLOY_DIR}"
        dry_log "Restore: .env.production, nginx.conf, docker-compose files, SSL certs"
    else
        gzip -t "${ACTUAL_CONFIG_FILE}" 2>/dev/null || error "Config backup gzip check failed"

        TMPDIR_RESTORE=$(mktemp -d)
        tar xzf "${ACTUAL_CONFIG_FILE}" -C "${TMPDIR_RESTORE}"

        EXTRACTED="${TMPDIR_RESTORE}/kaasb-configs"

        # Restore .env.production (with confirmation since it contains secrets)
        if [ -f "${EXTRACTED}/.env.production" ]; then
            cp "${EXTRACTED}/.env.production" "${ENV_FILE}"
            log "Restored: .env.production"
        fi

        # Restore nginx.conf
        if [ -f "${EXTRACTED}/nginx.conf" ]; then
            cp "${EXTRACTED}/nginx.conf" "${DEPLOY_DIR}/docker/nginx/nginx.conf"
            log "Restored: nginx.conf"
        fi

        # Restore postgresql.conf
        if [ -f "${EXTRACTED}/postgresql.conf" ]; then
            cp "${EXTRACTED}/postgresql.conf" "${DEPLOY_DIR}/docker/postgres/postgresql.conf"
            log "Restored: postgresql.conf"
        fi

        # Restore docker-compose files
        for f in docker-compose.prod.yml docker-compose.monitoring.yml; do
            if [ -f "${EXTRACTED}/${f}" ]; then
                cp "${EXTRACTED}/${f}" "${DEPLOY_DIR}/${f}"
                log "Restored: ${f}"
            fi
        done

        # Restore SSL certs into letsencrypt volume
        if [ -f "${EXTRACTED}/ssl-certs.tar.gz" ]; then
            cp "${EXTRACTED}/ssl-certs.tar.gz" /tmp/ssl-certs-restore.tar.gz
            docker run --rm \
                -v kaasb_letsencrypt:/letsencrypt \
                -v /tmp:/backup:ro \
                alpine:3.19 \
                sh -c 'rm -rf /letsencrypt/* && tar xzf /backup/ssl-certs-restore.tar.gz -C /letsencrypt'
            rm -f /tmp/ssl-certs-restore.tar.gz
            log "Restored: SSL certificates"
        fi

        rm -rf "${TMPDIR_RESTORE}"
        log "Configuration restore complete."
    fi
fi

# ---------------------------------------------------------------------------
# STEP 5: Restart services
# ---------------------------------------------------------------------------
if [ "${DO_DB}" = "true" ] || [ "${DO_CONFIG}" = "true" ]; then
    log "─── RESTARTING SERVICES ─────────────────────────────────"
    run "$COMPOSE up -d"

    if [ "${DRY_RUN}" = "false" ]; then
        log "Waiting for services to become healthy..."
        for i in $(seq 1 30); do
            if curl -sf http://localhost/api/v1/health > /dev/null 2>&1; then
                log "Platform is healthy."
                break
            fi
            sleep 5
        done
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  RESTORE COMPLETE                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
if [ "${DRY_RUN}" = "true" ]; then
    echo -e "  ${CYAN}DRY-RUN complete — no changes were made.${NC}"
    echo -e "  ${CYAN}Run without --dry-run to perform the actual restore.${NC}"
else
    [ "${DO_DB}" = "true" ]     && echo -e "  Database : ${GREEN}restored from $(basename "${DB_FILE}")${NC}"
    [ "${DO_FILES}" = "true" ]  && echo -e "  Files    : ${GREEN}restored from $(basename "${FILES_FILE}")${NC}"
    [ "${DO_CONFIG}" = "true" ] && echo -e "  Configs  : ${GREEN}restored from $(basename "${CONFIG_FILE}")${NC}"
fi
echo ""
log "Restore job finished — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
