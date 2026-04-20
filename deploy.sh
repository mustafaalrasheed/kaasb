#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Production Deployment Script
# =============================================================================
# Usage:
#   ./deploy.sh                 Full deploy (build locally + start)
#   ./deploy.sh --pull          Pull pre-built GHCR images + restart (fast)
#   ./deploy.sh --build         Build images locally only
#   ./deploy.sh --migrate       Run Alembic migrations
#   ./deploy.sh --restart       Restart all running services
#   ./deploy.sh --stop          Stop all services
#   ./deploy.sh --logs [svc]    Tail logs (optional: backend|frontend|nginx|db)
#   ./deploy.sh --status        Show container status
#   ./deploy.sh --backup        Manual database backup
#   ./deploy.sh --rollback      Restart with the previous image tag
#   ./deploy.sh --ssl           Obtain/renew SSL certificates
#   ./deploy.sh --create-admin  Create admin user interactively
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
info()  { echo -e "${BLUE}[INFO]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Require .env.production
# ---------------------------------------------------------------------------
ENV_FILE=".env.production"
[ -f "$ENV_FILE" ] || error "$ENV_FILE not found. Copy .env.production.example and fill in values."

# Enforce secure file permissions
chmod 600 "$ENV_FILE"

# Load variables safely — handles values with spaces and special chars
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ---------------------------------------------------------------------------
# Validate required variables
# ---------------------------------------------------------------------------
REQUIRED_VARS=(DB_USER DB_PASSWORD DB_NAME SECRET_KEY REDIS_PASSWORD DOMAIN)
for var in "${REQUIRED_VARS[@]}"; do
    [ -n "${!var:-}" ] || error "Required variable '$var' is empty in $ENV_FILE"
done

# ---------------------------------------------------------------------------
# Compose command
# ---------------------------------------------------------------------------
# Monitoring stack (Prometheus/Grafana/Alertmanager/exporters) is always
# deployed alongside the application. If you need to temporarily skip it,
# export SKIP_MONITORING=1 before running this script.
if [ "${SKIP_MONITORING:-0}" = "1" ]; then
    COMPOSE="docker compose -f docker-compose.prod.yml --env-file $ENV_FILE"
else
    COMPOSE="docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml --env-file $ENV_FILE"
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_check_ssl() {
    local cert="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    if [ ! -f "$cert" ]; then
        warn "SSL cert not found at $cert"
        warn "Run:  ./deploy.sh --ssl"
        return 1
    fi
    return 0
}

_wait_healthy() {
    local service="$1"
    local container="kaasb_${service}"
    local max_attempts=40   # 40 × 5s = 200s max
    info "Waiting for $service to become healthy..."
    for i in $(seq 1 $max_attempts); do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "missing")
        case "$STATUS" in
            healthy)  log "$service is healthy (attempt $i)"; return 0 ;;
            unhealthy) warn "$service is unhealthy" ; return 1 ;;
        esac
        sleep 5
    done
    warn "$service health check timed out after $((max_attempts * 5))s"
    return 1
}

_backup_db() {
    local label="${1:-manual}"
    local ts; ts=$(date +%Y%m%d-%H%M%S)
    local out="backups/kaasb-${label}-${ts}.sql"
    mkdir -p backups
    $COMPOSE exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" > "$out"
    log "Backup saved: $out"
}

# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------
case "${1:-full}" in

    --pull)
        log "Pulling GHCR images and restarting services..."
        $COMPOSE pull backend frontend
        _backup_db "pre-pull"
        $COMPOSE run --rm backend alembic upgrade head
        $COMPOSE up -d --no-deps backend
        _wait_healthy backend || { warn "Backend unhealthy after pull — check logs"; exit 1; }
        $COMPOSE up -d --no-deps frontend
        # Start/ensure all other services (monitoring stack, etc.) without
        # recreating the already-updated backend/frontend
        $COMPOSE up -d --no-recreate
        log "Pull + restart complete."
        ;;

    --build)
        log "Building images locally (no cache)..."
        $COMPOSE build --no-cache
        log "Build complete."
        ;;

    --migrate)
        log "Running Alembic migrations..."
        _backup_db "pre-migrate"
        $COMPOSE run --rm backend alembic upgrade head
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
        $COMPOSE logs -f --tail=100 "${2:-}"
        ;;

    --status)
        $COMPOSE ps
        ;;

    --backup)
        _backup_db "manual"
        ;;

    --rollback)
        if [ ! -f .release.previous ]; then
            error "No previous release recorded. Cannot rollback."
        fi
        PREV_TAG=$(cat .release.previous)
        CURR_TAG="${IMAGE_TAG:-latest}"
        log "Rolling back from ${CURR_TAG} → ${PREV_TAG}"
        sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${PREV_TAG}/" "$ENV_FILE"
        $COMPOSE pull backend frontend
        $COMPOSE up -d --no-deps backend frontend
        _wait_healthy backend && log "Rollback complete." || error "Rollback failed — check logs."
        ;;

    --ssl)
        log "Obtaining SSL certificate for ${DOMAIN}..."
        # Start nginx on port 80 only for ACME challenge
        docker run --rm -p 80:80 \
            -v /var/www/certbot:/var/www/certbot \
            nginx:alpine nginx -g "daemon off;" &
        NGINX_PID=$!
        sleep 2
        certbot certonly \
            --webroot \
            --webroot-path /var/www/certbot \
            --non-interactive \
            --agree-tos \
            --email "admin@${DOMAIN}" \
            -d "${DOMAIN}" \
            -d "www.${DOMAIN}"
        kill $NGINX_PID 2>/dev/null || true
        log "SSL cert obtained. Add a cron job:"
        info "  0 3 * * * certbot renew --quiet && docker exec kaasb_nginx nginx -s reload"
        ;;

    --create-admin)
        log "Creating admin user..."
        $COMPOSE exec backend python -m scripts.create_admin
        ;;

    full|--full)
        log "==================================================================="
        log "  Kaasb Full Production Deployment"
        log "==================================================================="
        echo ""

        # Pre-flight checks
        _check_ssl || warn "Continuing without SSL — platform will not serve HTTPS"

        # Save current IMAGE_TAG for rollback
        echo "${IMAGE_TAG:-latest}" > .release.previous

        # Step 1: Build
        log "Step 1/6: Building images..."
        $COMPOSE build

        # Step 2: Database + Redis
        log "Step 2/6: Starting database & Redis..."
        $COMPOSE up -d db redis
        _wait_healthy db    || error "Database failed to start"
        _wait_healthy redis || error "Redis failed to start"

        # Step 3: Pre-migration backup (if DB already has data)
        if $COMPOSE exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -c "\dt" 2>/dev/null | grep -q "users"; then
            log "Step 3/6: Backing up existing data..."
            _backup_db "pre-deploy"
        else
            log "Step 3/6: Skipping backup (fresh database)"
        fi

        # Step 4: Migrations
        log "Step 4/6: Running migrations..."
        $COMPOSE run --rm backend alembic upgrade head

        # Step 5: Start all services
        log "Step 5/6: Starting all services..."
        $COMPOSE up -d

        # Step 6: Health check
        log "Step 6/6: Verifying deployment..."
        _wait_healthy backend  || warn "Backend not yet healthy — may still be starting"
        _wait_healthy frontend || warn "Frontend not yet healthy — may still be starting"

        # Final HTTP check through nginx
        sleep 5
        if curl -sf "http://localhost/health" > /dev/null 2>&1; then
            log "Platform is LIVE at https://${DOMAIN}"
        else
            warn "HTTP health check failed — nginx may still be starting or SSL is not configured"
            warn "Check: ./deploy.sh --logs nginx"
        fi

        echo ""
        log "==================================================================="
        log "  Deployment Summary"
        log "==================================================================="
        $COMPOSE ps
        echo ""
        info "Useful commands:"
        echo "  ./deploy.sh --logs          # Follow all logs"
        echo "  ./deploy.sh --logs backend  # Backend logs"
        echo "  ./deploy.sh --status        # Container status"
        echo "  ./deploy.sh --backup        # Manual DB backup"
        echo "  ./deploy.sh --rollback      # Rollback to previous"
        echo "  ./deploy.sh --migrate       # Run migrations only"
        echo "  ./deploy.sh --create-admin  # Create admin user"
        echo "  ./deploy.sh --stop          # Stop everything"
        ;;

    *)
        echo "Usage: ./deploy.sh [--pull|--build|--migrate|--restart|--stop|--logs|--status|--backup|--rollback|--ssl|--create-admin|--full]"
        exit 1
        ;;
esac
