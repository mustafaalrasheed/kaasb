#!/bin/bash
# ============================================
# Kaasb Platform - Production Deployment
# ============================================
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh              # Full deploy
#   ./deploy.sh --build      # Build only
#   ./deploy.sh --migrate    # Migrate only
#   ./deploy.sh --restart    # Restart services
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Load env
if [ ! -f .env.production ]; then
    error ".env.production not found. Copy .env.production.example and fill in values."
fi

export $(grep -v '^#' .env.production | xargs)

# Validate required vars
for var in DB_USER DB_PASSWORD DB_NAME SECRET_KEY DOMAIN; do
    if [ -z "${!var}" ]; then
        error "Required variable $var is not set in .env.production"
    fi
done

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

case "${1:-full}" in
    --build)
        log "Building images..."
        $COMPOSE build
        log "Build complete!"
        ;;

    --migrate)
        log "Running migrations..."
        $COMPOSE exec backend alembic upgrade head
        log "Migrations complete!"
        ;;

    --restart)
        log "Restarting services..."
        $COMPOSE restart
        log "Services restarted!"
        ;;

    --stop)
        log "Stopping all services..."
        $COMPOSE down
        log "Stopped."
        ;;

    --logs)
        $COMPOSE logs -f ${2:-""}
        ;;

    --status)
        $COMPOSE ps
        ;;

    --create-admin)
        log "Creating admin user..."
        $COMPOSE exec backend python -m scripts.create_admin
        ;;

    full|--full)
        log "=== Full Production Deployment ==="
        echo ""

        log "Step 1/5: Building images..."
        $COMPOSE build --no-cache

        log "Step 2/5: Starting database & redis..."
        $COMPOSE up -d db redis
        sleep 5

        log "Step 3/5: Running migrations..."
        $COMPOSE run --rm backend alembic upgrade head

        log "Step 4/5: Starting all services..."
        $COMPOSE up -d

        log "Step 5/5: Health check..."
        sleep 10
        if curl -sf http://localhost/health > /dev/null 2>&1; then
            log "✅ Platform is live at http://${DOMAIN}"
        else
            warn "Health check failed — services may still be starting."
            warn "Check logs with: ./deploy.sh --logs"
        fi

        echo ""
        log "=== Deployment Summary ==="
        $COMPOSE ps
        echo ""
        log "Useful commands:"
        echo "  ./deploy.sh --logs          # View logs"
        echo "  ./deploy.sh --logs backend  # Backend logs only"
        echo "  ./deploy.sh --status        # Service status"
        echo "  ./deploy.sh --restart       # Restart all"
        echo "  ./deploy.sh --create-admin  # Create admin user"
        echo "  ./deploy.sh --stop          # Stop all"
        ;;

    *)
        echo "Usage: ./deploy.sh [--build|--migrate|--restart|--stop|--logs|--status|--create-admin|--full]"
        ;;
esac
