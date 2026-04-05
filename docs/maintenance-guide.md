# Kaasb — Maintenance Guide

## Server Access

```bash
ssh deploy@116.203.140.27 -p 2222
cd /opt/kaasb
```

---

## Daily Operations

### Morning health check (5 min)

```bash
# 1. Container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. API health
curl -s https://kaasb.com/api/v1/health | python3 -m json.tool

# 3. Recent errors (last 100 lines)
docker logs backend --tail=100 2>&1 | grep -E "ERROR|CRITICAL|500"

# 4. Disk usage
df -h /

# 5. Check Sentry dashboard for new issues
# → https://sentry.io (your project)
```

### What to look for

| Signal | Threshold | Action |
|--------|-----------|--------|
| Disk usage | > 80% | Run `docker system prune`, check backup retention |
| Backend errors | > 5 errors/hour | Check Sentry, restart backend if unresponsive |
| DB connections | > 80% of pool_size | Check for connection leaks, consider pool increase |
| Container status | not "Up" or "healthy" | Restart container, check logs |
| Memory usage | > 90% | Identify leak, consider server upgrade |

### Admin moderation queue

Log in to https://kaasb.com/admin daily to:
- Review pending gigs (approve/reject)
- Process payout queue (pay freelancers via QiCard, then mark paid)
- Review reported content

---

## Weekly Operations

### Dependency security scan

```bash
# Backend
cd /opt/kaasb
docker exec backend pip-audit

# Frontend (run locally or in CI)
cd frontend && npm audit
```

Fix any `critical` or `high` severity findings immediately. `moderate` can wait for next sprint.

### Disk and backup check

```bash
# Disk usage breakdown
du -sh /opt/kaasb/backups/*
du -sh /var/lib/docker/volumes/*
df -h

# Verify latest backup exists and is non-zero
ls -lh /opt/kaasb/backups/ | tail -10

# Test backup integrity (restore to temp DB)
BACKUP=$(ls /opt/kaasb/backups/*.sql.gz | tail -1)
gunzip -c $BACKUP | psql -U kaasb kaasb_test 2>&1 | tail -5
# Should show no errors
```

### Platform metrics review

Open Grafana:
```bash
# On your local machine:
ssh -L 3001:localhost:3001 deploy@116.203.140.27 -p 2222 -N &
# → http://localhost:3001
```

Check:
- Weekly registrations (clients vs freelancers)
- Order volume and completion rate
- Payment success rate
- p95 API latency (target: < 500ms)
- Error rate (target: < 0.1%)

### Dependabot PRs

Review and merge Dependabot PRs in GitHub. Always let CI pass before merging. Batch minor version bumps together.

---

## Monthly Operations

### Backup restore test

```bash
# Create a test database
docker exec postgres createdb -U kaasb kaasb_test

# Restore latest backup
BACKUP=$(ls /opt/kaasb/backups/*.sql.gz | tail -1)
gunzip -c $BACKUP | docker exec -i postgres psql -U kaasb kaasb_test

# Verify row counts match production
docker exec postgres psql -U kaasb -c "
SELECT 'users' as table, count(*) FROM kaasb.users
UNION ALL
SELECT 'jobs', count(*) FROM kaasb.jobs
UNION ALL
SELECT 'gigs', count(*) FROM kaasb.gigs;
" 

docker exec postgres psql -U kaasb kaasb_test -c "
SELECT 'users' as table, count(*) FROM users
UNION ALL
SELECT 'jobs', count(*) FROM jobs
UNION ALL
SELECT 'gigs', count(*) FROM gigs;
"

# Compare outputs — should match within last backup interval

# Cleanup
docker exec postgres dropdb -U kaasb kaasb_test
```

### Secrets rotation

Rotate these monthly:

```bash
# 1. JWT secret key
NEW_SECRET=$(openssl rand -hex 32)
# Update .env.production SECRET_KEY=<new_value>
# Restart backend — all existing sessions invalidated

# 2. Redis password (if changed)
# Update .env.production REDIS_PASSWORD=<new_value>
# Update redis.conf requirepass <new_value>
# Restart redis + backend

# 3. Check API key expiry
# QiCard API key — check merchant dashboard
# Resend API key — check resend.com dashboard
# Google OAuth secret — check console.cloud.google.com
```

### SSL certificate check

```bash
# Check expiry
docker exec nginx certbot certificates

# Manual renew (normally auto-renew via cron)
docker exec nginx certbot renew --dry-run   # Test
docker exec nginx certbot renew             # Actually renew
docker exec nginx nginx -s reload
```

Target: renew when < 30 days remaining. Let's Encrypt auto-renews at 60 days remaining.

### Package updates

```bash
# Backend
cd /opt/kaasb
docker exec backend pip list --outdated

# Frontend — run locally
cd frontend
npm outdated
npm update   # Minor/patch only. Major versions: read changelog first.

# After updates: run tests, commit, push → CI/CD deploys
```

### Docker cleanup

```bash
docker system prune -f              # Remove stopped containers + dangling images
docker image prune -a --filter "until=720h"  # Remove images older than 30 days
docker volume prune -f              # Remove unused volumes (careful — verify first)
```

---

## Database Management

### Connection monitoring

```bash
# Current connections
docker exec postgres psql -U kaasb -c "
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'kaasb'
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;
"

# Long-running queries (> 30 seconds)
docker exec postgres psql -U kaasb -c "
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE datname = 'kaasb'
  AND query_start IS NOT NULL
  AND now() - query_start > interval '30 seconds'
ORDER BY duration DESC;
"

# Kill stuck query
docker exec postgres psql -U kaasb -c "SELECT pg_cancel_backend(<pid>);"
```

### Performance monitoring

```bash
# Slow queries (requires pg_stat_statements — enabled by default)
docker exec postgres psql -U kaasb -c "
SELECT query, calls, mean_exec_time::int AS avg_ms, total_exec_time::int AS total_ms
FROM pg_stat_statements
WHERE mean_exec_time > 100   -- queries averaging > 100ms
ORDER BY mean_exec_time DESC
LIMIT 20;
"

# Table sizes
docker exec postgres psql -U kaasb -c "
SELECT relname AS table,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
"

# Index usage (low scans = unused index)
docker exec postgres psql -U kaasb -c "
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC
LIMIT 20;
"
```

### VACUUM and ANALYZE

```bash
# Weekly: analyze statistics (auto-vacuum usually handles this)
docker exec postgres psql -U kaasb -c "ANALYZE VERBOSE;"

# Monthly: full vacuum on heavily-updated tables
docker exec postgres psql -U kaasb -c "VACUUM ANALYZE users, jobs, gigs, notifications;"
```

### Manual backup

```bash
# Timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec postgres pg_dump -U kaasb kaasb | gzip > /opt/kaasb/backups/manual_$TIMESTAMP.sql.gz
ls -lh /opt/kaasb/backups/manual_$TIMESTAMP.sql.gz
```

---

## Container Management

### Check container status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"
```

### View logs

```bash
docker logs backend --tail=200 -f
docker logs frontend --tail=100 -f
docker logs nginx --tail=100 -f
docker logs postgres --tail=100 -f
docker logs redis --tail=100 -f
```

### Restart a container

```bash
docker restart backend
docker restart frontend
docker restart nginx
# Never restart postgres during active orders — use graceful stop
docker stop postgres && docker start postgres
```

### Resource usage

```bash
docker stats --no-stream
```

---

## Nginx Management

```bash
# Test nginx config before applying
docker exec nginx nginx -t

# Reload config (no downtime)
docker exec nginx nginx -s reload

# View access logs
docker exec nginx tail -f /var/log/nginx/access.log

# View error logs
docker exec nginx tail -f /var/log/nginx/error.log

# Check rate limit counters
docker exec nginx nginx -T | grep limit_req
```

---

## Development Workflow

### Feature development

```bash
# 1. Branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# 2. Develop and commit
git add <files>
git commit -m "feat(scope): description"

# 3. Push and open PR against develop
git push origin feature/my-feature
# → Open PR on GitHub → CI runs → merge

# 4. Automatic staging deploy on merge to develop
# → Verify on staging environment

# 5. PR from develop to main → automatic production deploy
```

### Hotfix (production bug)

```bash
# 1. Branch from main (NOT develop)
git checkout main
git pull origin main
git checkout -b fix/critical-bug

# 2. Fix, commit
git commit -m "fix(scope): description"

# 3. PR to main → merge → auto-deploy to production
# 4. Cherry-pick to develop (keep branches in sync)
git checkout develop
git cherry-pick <commit-hash>
git push origin develop
```

### Database migration workflow

```bash
# 1. Edit model in backend/app/models/
# 2. Generate migration
cd backend
alembic revision --autogenerate -m "describe_the_change"

# 3. Review generated file — check for:
#    - Enum creation: use DO $$ EXCEPTION WHEN duplicate_object pattern
#    - Enum columns in create_table: use postgresql.ENUM(..., create_type=False)
#    - Data migrations: add before schema changes

# 4. Apply and verify locally
alembic upgrade head
alembic check    # Must show: No new upgrade operations detected.

# 5. Commit with the model change
git add alembic/versions/ app/models/
git commit -m "feat(db): add <column> to <table>"

# 6. Push → CI/CD runs alembic upgrade head on deploy
```

---

## Emergency Procedures

### Site is down (5xx or not reachable)

```bash
# Step 1: Check all containers
docker ps

# Step 2: Check nginx (most common — bad config or upstream down)
docker logs nginx --tail=50
docker exec nginx nginx -t

# Step 3: Check backend
docker logs backend --tail=100 | grep ERROR
curl http://localhost:8000/api/v1/health

# Step 4: Restart in order
docker restart backend
docker restart frontend  
docker exec nginx nginx -s reload

# Step 5: If still down, check DB
docker exec postgres pg_isready -U kaasb
docker logs postgres --tail=50

# Step 6: Nuclear option (full restart)
cd /opt/kaasb
docker compose -f docker-compose.prod.yml restart
```

### Database connection exhausted

```bash
# Check connections
docker exec postgres psql -U kaasb -c "
SELECT count(*) FROM pg_stat_activity WHERE datname='kaasb';
"

# Kill idle connections older than 10 minutes
docker exec postgres psql -U kaasb -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'kaasb'
  AND state = 'idle'
  AND query_start < now() - interval '10 minutes';
"

# Restart backend (releases connection pool)
docker restart backend
```

### Disk space critical (> 95%)

```bash
# Find largest files
du -sh /opt/kaasb/backups/* | sort -rh | head -10
du -sh /var/lib/docker/volumes/* | sort -rh | head -10

# Clean old backups (keep last 14)
ls -t /opt/kaasb/backups/*.sql.gz | tail -n +15 | xargs rm -f

# Clean Docker
docker system prune -f
docker image prune -a -f

# Clean nginx logs
truncate -s 0 /var/log/nginx/access.log
```

### Bad deployment (new version breaking production)

```bash
# Option 1: Script rollback
cd /opt/kaasb
./deploy.sh --rollback

# Option 2: Revert commit + redeploy
git revert HEAD --no-edit
git push origin main
# → CI/CD triggers new deploy

# Option 3: Specify previous image tag
IMAGE_TAG=<previous-sha> docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend

# After rollback: run alembic downgrade if migration was included
docker exec backend alembic downgrade -1
```

### Security incident

```bash
# 1. Immediately suspend affected accounts (admin dashboard)

# 2. Rotate ALL secrets
openssl rand -hex 32   # New SECRET_KEY
# Update .env.production with all new values
./deploy.sh --pull     # Restart — invalidates all JWT tokens

# 3. Check audit log
docker exec postgres psql -U kaasb -c "
SELECT * FROM audit_log
WHERE created_at > now() - interval '24 hours'
ORDER BY created_at DESC
LIMIT 100;
"

# 4. Check for data exfiltration
docker logs backend --since 24h 2>&1 | grep -E "SELECT \*|EXPORT|pg_dump"

# 5. Notify affected users if PII was exposed
# → Send email via Resend explaining the incident

# 6. File incident report (date, scope, action taken, prevention)
```

### QiCard payment failing

```bash
# 1. Check circuit breaker state
docker logs backend --tail=50 | grep -i "qicard\|circuit"

# 2. Check QiCard API status (contact QiCard support)

# 3. If circuit is open (too many failures), restart backend to reset
docker restart backend

# 4. Test with sandbox mode
# Temporarily set QI_CARD_SANDBOX=true in .env.production
# Run test payment
# If sandbox works → production QiCard API issue → contact QiCard

# 5. Inform users of payment downtime via platform banner (admin settings)
```

---

## Useful One-Liners

```bash
# Count active users in last 24 hours
docker exec postgres psql -U kaasb -c "
SELECT count(*) FROM users WHERE last_login > now() - interval '24 hours';"

# Count orders by status
docker exec postgres psql -U kaasb -c "
SELECT status, count(*) FROM gig_orders GROUP BY status ORDER BY count DESC;"

# Count pending gig reviews
docker exec postgres psql -U kaasb -c "
SELECT count(*) FROM gigs WHERE status = 'pending_review';"

# Pending payouts (completed orders not yet paid)
docker exec postgres psql -U kaasb -c "
SELECT count(*), sum(freelancer_amount) FROM escrows WHERE status = 'released';"

# Backend uptime
docker inspect backend --format '{{.State.StartedAt}}'

# Redis memory
docker exec redis redis-cli INFO memory | grep used_memory_human

# Tail all logs simultaneously
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

---

## Monitoring URLs

| Service | URL / Access |
|---------|-------------|
| Site health | `curl https://kaasb.com/api/v1/health` |
| Grafana | `ssh -L 3001:localhost:3001 deploy@116.203.140.27 -p 2222 -N` → http://localhost:3001 |
| Sentry | https://sentry.io → Kaasb project |
| UptimeRobot | https://uptimerobot.com → your account |
| SSL check | https://ssllabs.com/ssltest/analyze.html?d=kaasb.com |
| Security headers | https://securityheaders.com/?q=kaasb.com |

---

## Post-Launch 48-Hour Plan

### Hour 0–2: Launch

- [ ] Deploy and verify all containers healthy
- [ ] Send test registration → verify email arrives
- [ ] Place test order → verify QiCard flow
- [ ] Check Sentry: zero errors
- [ ] Check Grafana: metrics flowing

### Hours 2–24: Monitor

- Check Sentry every 2 hours
- Monitor Grafana: request rate, error rate, latency
- Watch for unusual registration spikes (bot mitigation)
- Respond to any user-reported issues immediately

### Hours 24–48: Stabilize

- Review all Sentry issues, fix and deploy any critical bugs
- Check DB query performance — identify any slow queries from real traffic
- Verify backup ran successfully
- Check disk usage trend
- Review admin payout queue

### Week 1 priorities

1. Fix any bugs from beta users
2. Wire Twilio for real SMS OTP (currently email fallback)
3. Monitor QiCard success rate
4. Review and respond to first freelancer gig submissions

---

## Feature Roadmap (Post-Launch)

| Priority | Feature | Effort |
|----------|---------|--------|
| High | Redis pub/sub for cross-worker WebSocket messages | Medium |
| High | Twilio SMS for phone OTP (replace email beta) | Small |
| High | Live USD/IQD exchange rate feed | Small |
| Medium | `google_id` / `facebook_id` columns on users (prevent duplicate accounts) | Small |
| Medium | Gig order → QiCard payment wiring | Medium |
| Medium | Escrow for gig orders (currently job-marketplace only) | Medium |
| Medium | Full-text search with PostgreSQL tsvector on gigs | Medium |
| Low | Gig analytics dashboard (impressions, clicks, conversion funnel) | Large |
| Low | Automated QiCard payouts via API (when QiCard releases API) | Medium |
| Low | Freelancer verification badge | Small |
| Low | Dispute resolution center | Large |
| Low | Mobile app (React Native) | Extra Large |
| Low | Telegram notification bot | Medium |
