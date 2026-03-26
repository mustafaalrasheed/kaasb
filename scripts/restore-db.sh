#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Database Restore Script
# =============================================================================
# Usage:
#   bash /opt/kaasb/scripts/restore-db.sh                   # Interactive (picks latest)
#   bash /opt/kaasb/scripts/restore-db.sh /path/to/file.sql.gz
#
# ⚠ WARNING: This drops and recreates the database. All current data is lost.
# Run ONLY on the server, never in production without a fresh backup first.
# =============================================================================

set -euo pipefail

DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.prod.yml --env-file ${ENV_FILE}"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
log()   { echo -e "${GREEN}[RESTORE]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $*"; }
error() { echo -e "${RED}[ERROR]${NC}  $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
[ -f "$ENV_FILE" ] || error "$ENV_FILE not found"
set -a; source "$ENV_FILE"; set +a
[ -n "${DB_USER:-}"  ] || error "DB_USER not set"
[ -n "${DB_NAME:-}"  ] || error "DB_NAME not set"

# ---------------------------------------------------------------------------
# Select backup file
# ---------------------------------------------------------------------------
if [ -n "${1:-}" ]; then
    BACKUP_FILE="$1"
else
    # Pick the most recent daily backup automatically
    BACKUP_FILE=$(find "$BACKUP_DIR" -name "kaasb-*.sql.gz" -printf '%T@ %p\n' \
        | sort -rn | head -1 | cut -d' ' -f2-)
    [ -n "${BACKUP_FILE:-}" ] || error "No backup files found in $BACKUP_DIR"
fi

[ -f "$BACKUP_FILE" ] || error "File not found: $BACKUP_FILE"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
log "Backup file: $(basename "$BACKUP_FILE") (${BACKUP_SIZE})"

# ---------------------------------------------------------------------------
# Safety confirmation
# ---------------------------------------------------------------------------
echo ""
warn "This will DESTROY all data in database '${DB_NAME}' and restore from backup."
warn "Backup: $(basename "$BACKUP_FILE")"
echo ""
read -rp "Type 'yes' to confirm: " CONFIRM
[ "$CONFIRM" = "yes" ] || { log "Aborted."; exit 0; }

# ---------------------------------------------------------------------------
# Pre-restore safety backup of current state
# ---------------------------------------------------------------------------
log "Creating safety backup of current state..."
SAFETY="${BACKUP_DIR}/kaasb-pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
$COMPOSE exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip -9 > "${SAFETY}"
log "Safety backup saved: $(basename "${SAFETY}")"

# ---------------------------------------------------------------------------
# Stop application containers (leave DB running)
# ---------------------------------------------------------------------------
log "Stopping application containers..."
$COMPOSE stop backend frontend nginx 2>/dev/null || true

# ---------------------------------------------------------------------------
# Drop and recreate database
# ---------------------------------------------------------------------------
log "Dropping and recreating database '${DB_NAME}'..."
$COMPOSE exec -T db psql -U "${DB_USER}" -d postgres << SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "${DB_NAME}";
CREATE DATABASE "${DB_NAME}" OWNER "${DB_USER}";
GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO "${DB_USER}";
SQL

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
log "Restoring data (this may take a few minutes)..."
gunzip -c "${BACKUP_FILE}" | $COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1

# ---------------------------------------------------------------------------
# Verify basic table existence
# ---------------------------------------------------------------------------
log "Verifying restore..."
TABLE_COUNT=$($COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
log "Tables in public schema: ${TABLE_COUNT}"
[ "${TABLE_COUNT:-0}" -gt 0 ] || { warn "Restore may have failed — no tables found"; }

# ---------------------------------------------------------------------------
# Restart services and run any pending migrations
# ---------------------------------------------------------------------------
log "Running migrations on restored database..."
$COMPOSE run --rm backend alembic upgrade head

log "Restarting all services..."
$COMPOSE up -d

log "Waiting for health check..."
for i in $(seq 1 20); do
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        log "Platform is healthy after restore."
        break
    fi
    sleep 5
done

log "=========================================="
log "  Database restore complete."
log "  Source:  $(basename "${BACKUP_FILE}")"
log "  Tables:  ${TABLE_COUNT}"
log "  Safety backup: $(basename "${SAFETY}")"
log "=========================================="
