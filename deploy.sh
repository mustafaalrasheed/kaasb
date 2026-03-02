#!/bin/bash
# ============================================================
# Kaasb Platform - Production Deployment Script
# ============================================================
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh              # Full deployment (default)
#   ./deploy.sh --build      # Build images only
#   ./deploy.sh --migrate    # Run Alembic migrations only
#   ./deploy.sh --restart    # Restart all services
#   ./deploy.sh --stop       # Stop all services
#   ./deploy.sh --logs       # Tail all logs
#   ./deploy.sh --logs backend  # Tail a specific service
#   ./deploy.sh --status     # Show service status
#   ./deploy.sh --create-admin  # Create a superuser account
# ============================================================

set -euo pipefail

# ── Colours ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
info()  { echo -e "${BLUE}[INFO]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}   $1"; }
error() { echo -e "${RED}[ERROR]${NC}  $1"; exit 1; }

# ── Load environment ─────────────────────────────────────────
if [ ! -f .env.production ]; then
    error ".env.production not found. Copy .env.production.example and fill in the values."
fi

# Safe env loading — handles values with spaces, quotes, and special characters
set -a
# shellcheck disable=SC1091
. ./.env.production
set +a

# ── Validate required variables ──────────────────────────────
REQUIRED_VARS=(DB_USER DB_PASSWORD DB_NAME SECRET_KEY DOMAIN)
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        error "Required variable '$var' is not set in .env.production"
    fi
done

# Warn if SECRET_KEY is still the default placeholder
if [[ "${SECRET_KEY}" == *"change-me"* ]]; then
    warn "SECRET_KEY looks like the default placeholder — change it before deploying!"
fi

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

# ── Commands ─────────────────────────────────────────────────
case "${1:-full}" in

    --build)
        log "Building production images..."
        $COMPOSE build --no-cache
        log "Build complete."
        ;;

    --migrate)
        log "Running Alembic migrations..."
        $COMPOSE exec backend alembic upgrade head
        log "Migrations complete."
        ;;

    --restart)
        log "Restarting all services..."
        $COMPOSE restart
        log "Done."
        ;;

    --stop)
        log "Stopping all services..."
        $COMPOSE down
        log "Stopped."
        ;;

    --logs)
        $COMPOSE logs -f "${2:-}"
        ;;

    --status)
        $COMPOSE ps
        ;;

    --create-admin)
        log "Launching admin creation wizard..."
        $COMPOSE exec backend python -m scripts.create_admin
        ;;

    full|--full)
        log "================================================="
        log " Kaasb — Full Production Deployment"
        log "================================================="
        echo ""

        # Step 1: Build
        log "Step 1/5: Building production images (no-cache)..."
        $COMPOSE build --no-cache

        # Step 2: Start DB + Redis first so they are ready for migrations
        log "Step 2/5: Starting database and Redis..."
        $COMPOSE up -d db redis

        info "Waiting for database to become healthy..."
        for i in $(seq 1 30); do
            if $COMPOSE exec -T db pg_isready -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; then
                info "Database is ready."
                break
            fi
            if [ "$i" -eq 30 ]; then
                error "Database did not become healthy after 30 seconds."
            fi
            sleep 1
        done

        # Step 3: Run Alembic migrations before backend starts
        log "Step 3/5: Running database migrations..."
        $COMPOSE run --rm \
            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}" \
            backend alembic upgrade head
        log "Migrations complete."

        # Step 4: Start all services
        log "Step 4/5: Starting all services..."
        $COMPOSE up -d

        # Step 5: Health check with retry
        log "Step 5/5: Waiting for services to pass health checks..."
        sleep 15
        MAX_WAIT=60
        WAITED=0
        until curl -sf "http://localhost/health" > /dev/null 2>&1; do
            if [ "$WAITED" -ge "$MAX_WAIT" ]; then
                warn "Health check did not pass after ${MAX_WAIT}s — services may still be starting."
                warn "Run './deploy.sh --logs' to inspect."
                break
            fi
            sleep 3
            WAITED=$((WAITED + 3))
        done

        if curl -sf "http://localhost/health" > /dev/null 2>&1; then
            log "Platform is live at https://${DOMAIN}"
        fi

        echo ""
        log "================================================="
        log " Deployment Summary"
        log "================================================="
        $COMPOSE ps
        echo ""
        info "Useful commands:"
        echo "  ./deploy.sh --logs              # Tail all logs"
        echo "  ./deploy.sh --logs backend      # Backend logs only"
        echo "  ./deploy.sh --status            # Service status"
        echo "  ./deploy.sh --restart           # Restart all services"
        echo "  ./deploy.sh --create-admin      # Create admin user"
        echo "  ./deploy.sh --stop              # Stop all services"
        echo ""
        info "First time? Create your admin account:"
        echo "  ./deploy.sh --create-admin"
        ;;

    *)
        echo "Usage: ./deploy.sh [--build|--migrate|--restart|--stop|--logs [service]|--status|--create-admin|--full]"
        exit 1
        ;;
esac
