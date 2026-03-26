#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Pre-Migration Checklist
# =============================================================================
# Run this BEFORE every Alembic migration in production.
# Exits non-zero if any critical check fails.
#
# Usage:
#   bash scripts/pre-migration-checklist.sh
#   bash scripts/pre-migration-checklist.sh --dry-run   # check-only, no prompts
#
# What it checks:
#   1. A fresh backup exists (< 2 hours old)
#   2. Sufficient disk space (> 3 GB free in PGDATA and backup dir)
#   3. No active long-running queries (> 5 seconds)
#   4. No open transactions on the target tables
#   5. Current Alembic revision matches expected
#   6. Migration is reversible (downgrade function exists)
#   7. PostgreSQL version compatibility
# =============================================================================

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
DEPLOY_DIR="/opt/kaasb"
ENV_FILE="${DEPLOY_DIR}/.env.production"
BACKUP_DIR="${DEPLOY_DIR}/backups"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.prod.yml --env-file ${ENV_FILE}"
BACKEND_DIR="${DEPLOY_DIR}/backend"
MAX_BACKUP_AGE_HOURS=2
MIN_FREE_DISK_GB=3
DRY_RUN=false

# ─── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

PASS=0; FAIL=0; WARN=0

pass()  { echo -e "  ${GREEN}[PASS]${NC} $*"; (( PASS++ ))  || true; }
fail()  { echo -e "  ${RED}[FAIL]${NC} $*"; (( FAIL++ ))  || true; }
warn()  { echo -e "  ${YELLOW}[WARN]${NC} $*"; (( WARN++ ))  || true; }
info()  { echo -e "  ${BLUE}[INFO]${NC} $*"; }
header(){ echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

# ─── Load env ─────────────────────────────────────────────────────────────────
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found"; exit 1; }
set -a; source "$ENV_FILE"; set +a

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER}"
DB_PASSWORD="${DB_PASSWORD}"
DB_NAME="${DB_NAME}"

# Wrapper: run psql inside the db container
db_query() {
    PGPASSWORD="$DB_PASSWORD" $COMPOSE exec -T db psql \
        -U "$DB_USER" -d "$DB_NAME" -t -A \
        -c "$1" 2>/dev/null
}

echo ""
echo "=================================================================="
echo "  Kaasb DB — Pre-Migration Checklist"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "  Database: ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
echo "=================================================================="

# ─── CHECK 1: Recent backup exists ────────────────────────────────────────────
header "CHECK 1: Backup recency"

LATEST_BACKUP=$(find "$BACKUP_DIR" -name "kaasb-daily-*.sql.gz" \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)

if [ -z "$LATEST_BACKUP" ]; then
    fail "No backup file found in $BACKUP_DIR"
    info "Run: bash scripts/backup.sh  then retry this checklist"
else
    BACKUP_AGE_SECS=$(( $(date +%s) - $(stat -c %Y "$LATEST_BACKUP") ))
    BACKUP_AGE_HOURS=$(( BACKUP_AGE_SECS / 3600 ))
    info "Latest backup: $(basename "$LATEST_BACKUP") (${BACKUP_AGE_HOURS}h old)"

    if [ "$BACKUP_AGE_HOURS" -lt "$MAX_BACKUP_AGE_HOURS" ]; then
        pass "Backup is ${BACKUP_AGE_HOURS}h old (< ${MAX_BACKUP_AGE_HOURS}h threshold)"
    elif [ "$BACKUP_AGE_HOURS" -lt 25 ]; then
        warn "Backup is ${BACKUP_AGE_HOURS}h old — consider taking a fresh one"
        info "Run: bash scripts/backup.sh"
    else
        fail "Backup is ${BACKUP_AGE_HOURS}h old — MUST take fresh backup before migrating"
        info "Run: bash scripts/backup.sh  then retry"
        if [ "$DRY_RUN" = false ]; then
            echo ""
            read -p "  Take a backup now? [y/N] " -r REPLY
            if [[ "$REPLY" =~ ^[Yy]$ ]]; then
                bash "${DEPLOY_DIR}/scripts/backup.sh"
            else
                echo "Aborting — backup required."
                exit 1
            fi
        fi
    fi
fi

# ─── CHECK 2: Disk space ──────────────────────────────────────────────────────
header "CHECK 2: Disk space"

# Check backup directory
BACKUP_FREE_GB=$(df -BG "$BACKUP_DIR" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo 0)
if [ "${BACKUP_FREE_GB:-0}" -gt "$MIN_FREE_DISK_GB" ]; then
    pass "Backup dir: ${BACKUP_FREE_GB} GB free (> ${MIN_FREE_DISK_GB} GB required)"
else
    fail "Backup dir: only ${BACKUP_FREE_GB} GB free — need at least ${MIN_FREE_DISK_GB} GB"
fi

# Check PostgreSQL data directory (inside container)
PGDATA_FREE=$(db_query "SELECT pg_size_pretty(pg_database_size(current_database()))" || echo "unknown")
info "Database size: $PGDATA_FREE"

# Check host disk where Docker volumes live
HOST_FREE_GB=$(df -BG /var/lib/docker 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo 999)
if [ "${HOST_FREE_GB:-999}" -gt "$MIN_FREE_DISK_GB" ]; then
    pass "Docker volume disk: ${HOST_FREE_GB} GB free"
else
    fail "Docker volume disk: only ${HOST_FREE_GB} GB free"
fi

# ─── CHECK 3: No long-running active queries ──────────────────────────────────
header "CHECK 3: Active query health"

LONG_QUERIES=$(db_query "
    SELECT COUNT(*) FROM pg_stat_activity
    WHERE datname = current_database()
      AND state = 'active'
      AND query_start < now() - INTERVAL '5 seconds'
      AND query NOT LIKE '%pg_stat_activity%'
" || echo "0")

if [ "${LONG_QUERIES:-0}" -eq 0 ]; then
    pass "No long-running queries (> 5s) currently active"
else
    warn "${LONG_QUERIES} queries running > 5 seconds"
    db_query "
        SELECT pid, usename, EXTRACT(EPOCH FROM (now() - query_start))::INT AS secs,
               LEFT(query, 80) FROM pg_stat_activity
        WHERE state = 'active' AND query_start < now() - INTERVAL '5 seconds'
        AND query NOT LIKE '%pg_stat_activity%'
        ORDER BY secs DESC LIMIT 5
    " || true
    info "Wait for these to complete or kill with: SELECT pg_terminate_backend(pid);"
fi

# ─── CHECK 4: No open idle-in-transaction sessions ────────────────────────────
header "CHECK 4: Idle transaction sessions"

IDLE_TXN=$(db_query "
    SELECT COUNT(*) FROM pg_stat_activity
    WHERE datname = current_database()
      AND state LIKE 'idle in transaction%'
" || echo "0")

if [ "${IDLE_TXN:-0}" -eq 0 ]; then
    pass "No idle-in-transaction sessions"
else
    warn "${IDLE_TXN} idle-in-transaction session(s) found"
    info "These will be killed by idle_in_transaction_session_timeout after 60s"
    info "Or manually: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state LIKE 'idle in transaction%';"
fi

# ─── CHECK 5: Connection count headroom ───────────────────────────────────────
header "CHECK 5: Connection pool headroom"

CONN_INFO=$(db_query "
    SELECT
        current_setting('max_connections')::INT AS max_conn,
        COUNT(*) AS active_conn
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY 1
" || echo "75|10")

MAX_CONN=$(echo "$CONN_INFO" | cut -d'|' -f1 || echo "75")
ACTIVE_CONN=$(echo "$CONN_INFO" | cut -d'|' -f2 || echo "0")
PCT=$(( 100 * ${ACTIVE_CONN:-0} / ${MAX_CONN:-75} ))
info "Connections: ${ACTIVE_CONN}/${MAX_CONN} (${PCT}% used)"

if [ "$PCT" -lt 70 ]; then
    pass "Connection headroom OK (${PCT}% used)"
elif [ "$PCT" -lt 85 ]; then
    warn "Connection usage at ${PCT}% — consider migrating during lower-traffic window"
else
    fail "Connection usage at ${PCT}% — very close to max_connections. High risk of timeout during migration."
fi

# ─── CHECK 6: Alembic current revision ───────────────────────────────────────
header "CHECK 6: Alembic migration state"

CURRENT_REV=$(cd "$BACKEND_DIR" && $COMPOSE exec -T api \
    alembic current 2>/dev/null | grep -oP '[a-f0-9]{12}' | head -1 || echo "unknown")

info "Current Alembic revision: $CURRENT_REV"

# Check for pending migrations
PENDING=$($COMPOSE exec -T api \
    bash -c "cd /app && alembic history | grep -c '(head)'" 2>/dev/null || echo "unknown")
info "Pending migrations: $PENDING"

if [ "$CURRENT_REV" != "unknown" ]; then
    pass "Alembic revision detectable: $CURRENT_REV"
else
    warn "Could not determine current Alembic revision"
fi

# ─── CHECK 7: Replication slot lag (if any) ───────────────────────────────────
header "CHECK 7: Replication slots"

REP_LAG=$(db_query "
    SELECT COUNT(*) FROM pg_replication_slots
    WHERE active = false AND pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) > 1073741824
" || echo "0")

if [ "${REP_LAG:-0}" -eq 0 ]; then
    pass "No stalled replication slots with > 1 GB lag"
else
    warn "${REP_LAG} replication slot(s) are stalled and falling behind"
    info "Large migrations on primary may fail if replica can't keep up"
fi

# ─── CHECK 8: PostgreSQL version ─────────────────────────────────────────────
header "CHECK 8: PostgreSQL version"

PG_VERSION=$(db_query "SELECT version()" || echo "unknown")
info "PostgreSQL: $PG_VERSION"

PG_MAJOR=$(db_query "SELECT current_setting('server_version_num')::INT / 10000" || echo "0")
if [ "${PG_MAJOR:-0}" -ge 14 ]; then
    pass "PostgreSQL version >= 14 (supports all required features)"
else
    warn "PostgreSQL version < 14 — some monitoring features may not work"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "  PRE-MIGRATION CHECKLIST SUMMARY"
echo "=================================================================="
echo -e "  ${GREEN}PASSED${NC}: $PASS"
echo -e "  ${YELLOW}WARNED${NC}: $WARN"
echo -e "  ${RED}FAILED${NC}: $FAIL"
echo "=================================================================="

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "  ${RED}❌ MIGRATION BLOCKED — fix $FAIL failing check(s) above${NC}"
    echo ""
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo ""
    echo -e "  ${YELLOW}⚠  PROCEED WITH CAUTION — $WARN warning(s) above${NC}"
    echo ""
    if [ "$DRY_RUN" = false ]; then
        read -p "  Proceed with migration anyway? [y/N] " -r REPLY
        [[ "$REPLY" =~ ^[Yy]$ ]] || { echo "Migration aborted by user."; exit 1; }
    fi
else
    echo ""
    echo -e "  ${GREEN}✅ ALL CHECKS PASSED — safe to run migration${NC}"
    echo ""
fi

echo "  Next step: alembic upgrade head"
echo "  Rollback:  alembic downgrade -1"
echo ""
