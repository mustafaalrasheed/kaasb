# Kaasb — Deployment Guide

## Overview

- **Server:** Hetzner CPX22 — 3 vCPU / 4 GB RAM / 80 GB NVMe / Ubuntu 24.04
- **IP:** 116.203.140.27
- **Domain:** kaasb.com
- **App directory:** `/opt/kaasb`
- **Deploy user:** `deploy` (SSH key only, no password)

All services run as Docker containers managed by Docker Compose.

---

## Prerequisites (One-Time Setup)

These steps are done once on a fresh server. Skip if already configured.

### 1. Server Access

```bash
ssh root@116.203.140.27
```

### 2. Run Setup Script

```bash
# On your local machine, copy the script
scp server-setup.sh root@116.203.140.27:/tmp/

# On the server
chmod +x /tmp/server-setup.sh
bash /tmp/server-setup.sh
```

The setup script:
- Updates system packages
- Creates `deploy` user with sudo
- Configures SSH hardening (port 2222, key-only, disable root login)
- Sets up UFW firewall (allow 2222, 80, 443)
- Installs Docker + Docker Compose
- Creates 4 GB swap file
- Enables unattended security updates
- Configures fail2ban

### 3. GitHub Actions Secrets

In your GitHub repo → Settings → Secrets → Actions, add:

| Secret | Value |
|--------|-------|
| `HETZNER_SSH_KEY` | Private SSH key for deploy user |
| `HETZNER_HOST` | `116.203.140.27` |
| `HETZNER_USER` | `deploy` |
| `GHCR_TOKEN` | GitHub PAT with `packages:read` |

---

## Initial Production Deployment

### 1. SSH to server

```bash
ssh deploy@116.203.140.27 -p 2222
```

### 2. Clone repository

```bash
cd /opt
sudo git clone https://github.com/mustafaalrasheed/kaasb.git
sudo chown -R deploy:deploy /opt/kaasb
cd /opt/kaasb
```

### 3. Create production environment file

```bash
cp .env.production.example .env.production
nano .env.production
```

Fill in ALL values. Critical ones:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://kaasb:STRONG_PASSWORD@postgres:5432/kaasb
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
SECRET_KEY=<generate: openssl rand -hex 32>
DOMAIN=kaasb.com

# Payments
QI_CARD_API_KEY=your_key_here
QI_CARD_SANDBOX=false

# Email
RESEND_API_KEY=re_xxxxxxxxxxxx
EMAIL_FROM=noreply@kaasb.com

# OAuth
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxx
FACEBOOK_APP_ID=xxxx
FACEBOOK_APP_SECRET=xxxx

# DB credentials (used by docker-compose)
DB_USER=kaasb
DB_PASSWORD=STRONG_PASSWORD
DB_NAME=kaasb
REDIS_PASSWORD=REDIS_PASSWORD

# Monitoring
SENTRY_DSN=https://xxxx@sentry.io/xxxx

# Frontend
NEXT_PUBLIC_API_URL=https://kaasb.com/api/v1
NEXT_PUBLIC_BACKEND_URL=https://kaasb.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
NEXT_PUBLIC_FACEBOOK_APP_ID=xxxx
```

### 4. Validate environment

```bash
bash scripts/validate-env.sh
```

Fix any reported issues before continuing.

### 5. Deploy

```bash
./deploy.sh full
```

This runs:
1. `docker compose -f docker-compose.prod.yml pull` — pull latest images
2. `docker compose -f docker-compose.prod.yml up -d` — start all services
3. `docker exec backend alembic upgrade head` — run migrations
4. Health check — verify all containers are healthy

### 6. Post-deploy setup

```bash
# Seed gig categories (idempotent)
docker exec backend python scripts/seed_categories.py

# Create admin user
docker exec -it backend python scripts/create_admin.py
# → Enter admin email and password when prompted
```

### 7. SSL Certificates

```bash
./deploy.sh --ssl
# → Runs certbot, configures nginx, sets up auto-renew cron
```

### 8. Verify

```bash
# All containers healthy
docker ps

# API responding
curl https://kaasb.com/api/v1/health

# Frontend loading
curl -I https://kaasb.com

# SSL grade
# → Visit https://ssllabs.com/ssltest/analyze.html?d=kaasb.com
```

---

## Routine Deployments (CI/CD)

After initial setup, all deployments happen automatically via GitHub Actions:

```
Push to develop → CI (lint + test + build) → deploy to staging
Push to main    → CI (lint + test + build) → deploy to production
```

### Manual deploy (emergency)

```bash
ssh deploy@116.203.140.27 -p 2222
cd /opt/kaasb
./deploy.sh full
```

### Deploy options

```bash
./deploy.sh full          # Full: pull + up + migrate + health check
./deploy.sh --pull        # Pull latest images, restart containers
./deploy.sh --migrate     # Run alembic upgrade head only
./deploy.sh --rollback    # Roll back to previous Docker image tag
./deploy.sh --backup      # Manual pg_dump backup
./deploy.sh --ssl         # Renew SSL certificates
./deploy.sh --status      # Show container health + recent logs
./deploy.sh --logs        # Tail all container logs
./deploy.sh --create-admin # Create admin user interactively
```

---

## Database Migrations

### Before deploying schema changes

```bash
# Local: generate migration
cd backend
alembic revision --autogenerate -m "add_column_x_to_table_y"

# Review the generated file in alembic/versions/
# Always check for:
# - Enum creation (use DO $$ ... EXCEPTION WHEN duplicate_object pattern)
# - Enum columns in op.create_table (use postgresql.ENUM(..., create_type=False))
# - Data migrations (add before schema changes, test rollback)

# Apply locally
alembic upgrade head
alembic check   # Must show zero differences

# Commit and push — CI/CD runs migrations on deploy
```

### Emergency rollback migration

```bash
# On server
docker exec backend alembic downgrade -1   # One step back
# OR
docker exec backend alembic downgrade <revision_id>
```

---

## Rollback Procedure

If a deploy breaks production:

```bash
# Option 1: Script rollback (uses previous Docker image tag)
./deploy.sh --rollback

# Option 2: Git revert + redeploy
git revert HEAD
git push origin main
# → CI/CD triggers new deploy automatically

# Option 3: Manual image rollback
docker compose -f docker-compose.prod.yml \
  -e IMAGE_TAG=<previous_tag> up -d --no-deps backend frontend
```

---

## Environment Variables Update

To update env vars without full redeploy:

```bash
ssh deploy@116.203.140.27 -p 2222
nano /opt/kaasb/.env.production
# Edit values

cd /opt/kaasb
./deploy.sh --pull   # Restart containers with new env
```

---

## Staging Environment

Staging mirrors production but uses `develop` branch and a separate `.env.staging` file. The `staging.yml` GitHub Actions workflow deploys automatically on push to `develop`.

To access staging:
```bash
ssh deploy@116.203.140.27 -p 2222
cd /opt/kaasb-staging
./deploy.sh --status
```

---

## Docker Compose Services

```yaml
services:
  backend:    FastAPI via Gunicorn (5 workers × Uvicorn)
  frontend:   Next.js standalone build
  postgres:   PostgreSQL 16 (data volume: pgdata)
  redis:      Redis 7 (data volume: redisdata)
  nginx:      Reverse proxy + SSL (volumes: nginx.conf, certbot)
  prometheus: Metrics collection
  grafana:    Dashboards (data volume: grafana_data)
  alertmanager: Alert routing
```

All service logs:
```bash
docker compose -f docker-compose.prod.yml logs -f [service_name]
```

---

## Secrets Rotation

Rotate secrets in this order to minimize downtime:

1. Generate new value (e.g., `openssl rand -hex 32` for SECRET_KEY)
2. Update `.env.production` on server
3. Run `./deploy.sh --pull` to restart with new value
4. For SECRET_KEY rotation: all active sessions invalidated — users must log in again (acceptable for planned maintenance)
5. For DB password: update PostgreSQL first (`ALTER USER kaasb PASSWORD '...'`), then `.env.production`, then restart backend

---

## DNS Configuration

| Record | Type | Value | TTL |
|--------|------|-------|-----|
| `kaasb.com` | A | 116.203.140.27 | 300 |
| `www.kaasb.com` | A | 116.203.140.27 | 300 |

Nginx handles www → non-www redirect.

**Before any deployment with DNS changes:** lower TTL to 60 seconds at least 24 hours in advance.

---

## Pre-Launch Checklist

- [ ] `.env.production` has all values (validate-env.sh passes)
- [ ] `QI_CARD_SANDBOX=false` (live payments)
- [ ] `RESEND_API_KEY` set — send a test email
- [ ] Google OAuth: `https://kaasb.com` added to Authorized Origins + Redirect URIs
- [ ] Facebook Login: app in Live mode (not Development)
- [ ] Sentry receiving events — trigger a test error
- [ ] UptimeRobot monitoring `/health` every 5 min
- [ ] Backup cron verified — check `/opt/kaasb/backups/`
- [ ] SSL A+ on ssllabs.com
- [ ] Security headers A+ on securityheaders.com
- [ ] Admin account created and tested
- [ ] Seed categories verified in DB
- [ ] All containers `healthy` in `docker ps`
