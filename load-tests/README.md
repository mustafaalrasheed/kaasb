# Kaasb Load Testing Suite

Complete load, stress, spike, soak, and breakpoint tests for the Kaasb freelancing platform.
Tests simulate realistic Iraqi market traffic patterns — peak hours, Arabic content, IQD pricing.

---

## Quick Start

### 1. Install dependencies

```bash
# Python tools (Locust + seeder + analyzer)
pip install -r load-tests/requirements.txt

# k6 (separate binary)
# macOS:   brew install k6
# Linux:   sudo apt install k6   OR   sudo snap install k6
# Windows: choco install k6
```

### 2. Set your target URL

```bash
export TARGET=http://localhost:8000        # Local dev
export TARGET=http://staging.kaasb.com    # Staging
# NEVER run breakpoint or spike tests on production
```

### 3. Seed the database (optional but recommended)

```bash
python load-tests/data/seed_db.py --host $TARGET --clients 50 --freelancers 100 --jobs 200
```

---

## Test Types

| Test | File | Users | Duration | Purpose |
|------|------|-------|----------|---------|
| **Smoke** | k6/baseline.js | 2 | 2 min | Sanity check after deploy |
| **Baseline** | k6/baseline.js | 50 | 30 min | Normal daily load |
| **Stress** | k6/stress.js | 150–250 | 35 min | Find degradation point |
| **Spike** | k6/spike.js | 500 | 12 min | Viral traffic burst |
| **Soak** | k6/soak.js | 30 | 4 hours | Memory leaks, connection exhaustion |
| **Breakpoint** | k6/breakpoint.js | 1000 | 40 min | Find maximum capacity |
| **Race Conditions** | locust/race_conditions.py | 50 | 3 min | Concurrent operation safety |
| **Full Flow (Locust)** | locust/locustfile.py | 100 | custom | Complete user journey |
| **WebSocket** | k6/websocket.js | 200 | 10 min | Real-time chat load |

---

## Running Each Test

### Smoke test (run after EVERY deploy)

```bash
k6 run --env BASE_URL=$TARGET \
  --vus 2 --duration 2m \
  load-tests/k6/baseline.js
```

Expected: all green, no failures, p95 < 1000ms.

---

### Baseline load test

```bash
k6 run --env BASE_URL=$TARGET \
  --out csv=load-tests/reports/baseline.csv \
  load-tests/k6/baseline.js

# Analyze results:
python load-tests/analysis/analyze_results.py \
  --type k6 --file load-tests/reports/baseline.csv --test baseline
```

**Pass criteria:** Error rate < 1%, p95 < 2000ms, p99 < 5000ms

---

### Stress test (staging only)

```bash
k6 run --env BASE_URL=$TARGET \
  --out csv=load-tests/reports/stress.csv \
  load-tests/k6/stress.js

python load-tests/analysis/analyze_results.py \
  --type k6 --file load-tests/reports/stress.csv --test stress
```

**Watch:** Grafana DB pool panel — connection count should not max out.
**Pass criteria:** Error rate < 5% under 3× load, p95 < 5000ms

---

### Spike test (staging only)

```bash
k6 run --env BASE_URL=$TARGET \
  --out csv=load-tests/reports/spike.csv \
  load-tests/k6/spike.js
```

**Key question:** Does error rate recover to < 1% within 2 minutes of spike ending?
Watch the Grafana "Request Rate" panel — it should return to baseline after the spike.

---

### Soak test / endurance (staging only)

```bash
# Full 4-hour run — use screen/tmux so it survives SSH disconnect
screen -S soak
k6 run --env BASE_URL=$TARGET \
  --env HEALTH_TOKEN=your-health-bearer-token \
  --out csv=load-tests/reports/soak.csv \
  load-tests/k6/soak.js

# While running, watch Grafana for:
# - Memory growth in cAdvisor panel
# - DB connection count
# - Redis memory usage
# - Container restart count (must stay 0)
```

**Pass criteria:** Error rate stays < 1% all 4 hours, p95 doesn't drift > 20%.

---

### Breakpoint test ⚠️ (staging ONLY — will break system)

```bash
# WARNING: This WILL bring down the system. NEVER run on production.
k6 run --env BASE_URL=http://staging.kaasb.com \
  --out csv=load-tests/reports/breakpoint.csv \
  load-tests/k6/breakpoint.js

# Summary automatically saved to:
cat load-tests/reports/breakpoint_summary.json
```

Document the breaking point: "Kaasb breaks at ~XXX concurrent users / ~YYY RPS"

---

### Race condition test

```bash
cd load-tests
locust -f locust/race_conditions.py \
  --host $TARGET \
  --users 50 --spawn-rate 50 \
  --run-time 3m --headless \
  --csv reports/race_conditions
```

**Pass criteria:** Zero 500 errors. Any 500 = race condition bug to fix.

---

### Full Locust flow test (with Web UI)

```bash
cd load-tests
locust -f locust/locustfile.py --host $TARGET
# Open browser: http://localhost:8089
# Set: Users=100, Spawn rate=10
# Click Start
```

User distribution:
- **BrowseUser** (60%): anonymous browsing, job/freelancer search
- **AuthUser** (10%): login, profile, notifications
- **ClientUser** (10%): post jobs, review proposals, contracts
- **FreelancerUser** (15%): search jobs, submit proposals
- **ChatUser** (5%): conversations, messages

---

### WebSocket load test

```bash
k6 run --env BASE_URL=$TARGET \
  load-tests/k6/websocket.js
```

**Pass criteria:** 95%+ connections accepted, p95 message latency < 500ms.

Note: Kaasb uses in-memory WebSocket state (per Gunicorn worker). Under multi-worker
load, WebSocket state is not shared between workers. A client connected to worker 1
won't receive messages sent to worker 2. This is a known architectural limitation —
fix with Redis pub/sub if needed.

---

## Data Generator

Generate test data independently:

```bash
# Print sample data
python load-tests/data/generator.py

# Seed staging database
python load-tests/data/seed_db.py \
  --host http://staging.kaasb.com \
  --clients 50 \
  --freelancers 100 \
  --jobs 200

# Dry run (no requests, just show what would be created)
python load-tests/data/seed_db.py --dry-run
```

---

## Analyzing Results

### k6 CSV output

```bash
# Baseline
python load-tests/analysis/analyze_results.py \
  --type k6 --file reports/baseline.csv --test baseline

# Stress
python load-tests/analysis/analyze_results.py \
  --type k6 --file reports/stress.csv --test stress

# Save JSON report
python load-tests/analysis/analyze_results.py \
  --type k6 --file reports/soak.csv --test soak \
  --output reports/soak_report.json
```

### Locust CSV output

```bash
python load-tests/analysis/analyze_results.py \
  --type locust \
  --file reports/results_stats.csv \
  --test baseline
```

---

## Performance Baselines (Expected SLAs)

| Endpoint | p95 Target | Error Rate Target |
|----------|-----------|------------------|
| `GET /jobs` (search) | < 1500ms | < 0.5% |
| `GET /jobs/:id` | < 500ms | < 0.1% |
| `GET /users/freelancers` | < 1500ms | < 0.5% |
| `POST /auth/register` | < 3000ms | < 1.0% |
| `POST /auth/login` | < 1000ms | < 0.5% |
| `GET /auth/me` | < 200ms | < 0.1% |
| `POST /jobs` | < 1000ms | < 0.5% |
| `GET /health` | < 100ms | 0% |
| `GET /notifications/unread-count` | < 300ms | < 0.1% |
| `GET /contracts/my` | < 500ms | < 0.1% |

Note: `POST /auth/register` is slow because of bcrypt hashing (intentional — security vs performance).
Under spike load, bcrypt can become the bottleneck. Consider: bcrypt rounds = 10 (not 12+) in production.

---

## Monitoring During Tests

Open Grafana SSH tunnel while tests run:

```bash
# Terminal 1: tunnel
ssh -L 3001:localhost:3001 root@YOUR_SERVER_IP -N

# Browser: http://localhost:3001
```

Grafana panels to watch:

| Panel | What to look for |
|-------|----------------|
| Request Rate | Should increase proportionally to VU count |
| Error Rate | Should stay near 0% during baseline |
| p95 Latency | Baseline < 2s; rises under stress |
| DB Pool (checked_out) | Should not hit max (configured at 20) |
| DB Pool (overflow) | Should stay 0; if > 0, pool is exhausted |
| Redis Memory | Should grow slowly and stabilize |
| Container Memory | Should be flat (no growth = no memory leak) |
| Container CPU | Backend should use 80-100% at peak (expected) |

---

## CI/CD Integration

Add smoke + baseline tests to GitHub Actions:

```yaml
# In .github/workflows/ci.yml (add as new job):
load-test:
  name: Load Test (smoke)
  runs-on: ubuntu-latest
  needs: [backend, frontend]
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - name: Install k6
      run: |
        sudo apt-get install -y gnupg
        curl -s https://dl.k6.io/key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/k6-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt-get update && sudo apt-get install k6

    - name: Smoke test (2 users, 2 min)
      run: |
        k6 run --env BASE_URL=${{ secrets.STAGING_URL }} \
          --vus 2 --duration 2m \
          --out csv=smoke_results.csv \
          load-tests/k6/baseline.js

    - name: Analyze results
      run: |
        pip install pandas tabulate
        python load-tests/analysis/analyze_results.py \
          --type k6 --file smoke_results.csv --test smoke
```

---

## Finding Log

| ID | Test Type | Flow | Target | Pass Criteria | File |
|----|-----------|------|--------|---------------|------|
| KAASB-LOAD-001 | Baseline | Browse + Auth | 50 VUs / 30 min | p95 < 2s, errors < 1% | k6/baseline.js |
| KAASB-LOAD-002 | Stress | All flows | 250 VUs peak | p95 < 5s, errors < 5% | k6/stress.js |
| KAASB-LOAD-003 | Spike | Browse (viral) | 500 VUs in 30s | Recovery < 2 min | k6/spike.js |
| KAASB-LOAD-004 | Soak | All flows | 30 VUs / 4h | p95 drift < 20% | k6/soak.js |
| KAASB-LOAD-005 | Breakpoint | All flows | Until failure | Document breaking point | k6/breakpoint.js |
| KAASB-LOAD-006 | Race | Concurrent proposals | Same job_id | Zero 500 errors | locust/race_conditions.py |
| KAASB-LOAD-007 | Race | Concurrent messages | Same conv_id | Zero 500 errors | locust/race_conditions.py |
| KAASB-LOAD-008 | Race | Login storm | Same credentials | Zero 500 errors | locust/race_conditions.py |
| KAASB-LOAD-009 | WebSocket | WS connections | 200 concurrent | 95%+ connected, p95 < 500ms | k6/websocket.js |
| KAASB-LOAD-010 | Full flow | Client journey | 10% of VUs | p95 < 3s end-to-end | locust/locustfile.py |
| KAASB-LOAD-011 | Full flow | Freelancer journey | 15% of VUs | p95 < 3s end-to-end | locust/locustfile.py |
| KAASB-LOAD-012 | Full flow | Anonymous browse | 60% of VUs | p95 < 1.5s search | locust/locustfile.py |
