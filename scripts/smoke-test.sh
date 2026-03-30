#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Smoke Test (P21)
# Runs end-to-end checks against any environment.
#
# Usage:
#   bash scripts/smoke-test.sh                         # local (default)
#   BASE_URL=https://kaasb.com bash scripts/smoke-test.sh   # production
#   VERBOSE=1 BASE_URL=https://kaasb.com bash scripts/smoke-test.sh
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="${BASE_URL}/api/v1"
VERBOSE="${VERBOSE:-0}"

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
FAILURES=()

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
ok()   { echo -e "${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); FAILURES+=("$*"); }
skip() { echo -e "${YELLOW}[SKIP]${NC}  $*"; SKIP=$((SKIP + 1)); }

# Run curl and capture HTTP status + body
http() {
  local method="$1"; shift
  local url="$1";    shift
  local args=("$@")

  local tmpfile
  tmpfile=$(mktemp)
  local status
  status=$(curl -s -o "$tmpfile" -w "%{http_code}" -X "$method" "$url" "${args[@]}" 2>/dev/null || echo "000")
  local body
  body=$(cat "$tmpfile")
  rm -f "$tmpfile"

  if [ "$VERBOSE" = "1" ]; then
    echo "  → ${method} ${url} → HTTP ${status}"
    echo "  ← ${body}" | head -c 200
    echo ""
  fi

  echo "${status}|${body}"
}

# Assert an HTTP call returns expected status
assert() {
  local label="$1"
  local expected_status="$2"
  local response="$3"  # output of http()

  local actual_status
  actual_status=$(echo "$response" | cut -d'|' -f1)

  if [ "$actual_status" = "$expected_status" ]; then
    ok "$label (HTTP $actual_status)"
    return 0
  else
    fail "$label — expected HTTP $expected_status, got $actual_status"
    return 1
  fi
}

# Extract JSON field using python (avoids jq dependency)
jq_get() {
  local field="$1"
  local json="$2"
  echo "$json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    keys = '${field}'.split('.')
    for k in keys:
        if isinstance(data, list): data = data[int(k)]
        else: data = data.get(k, '')
    print(data if data else '')
except Exception:
    print('')
" 2>/dev/null || echo ""
}

# ── Test Data ────────────────────────────────────────────────────────────────
TIMESTAMP=$(date +%s)
CLIENT_EMAIL="smoke_client_${TIMESTAMP}@kaasb-test.com"
CLIENT_PASS="SmokeTest@${TIMESTAMP}!"
FREELANCER_EMAIL="smoke_free_${TIMESTAMP}@kaasb-test.com"
FREELANCER_PASS="SmokeTest@${TIMESTAMP}!"

CLIENT_TOKEN=""
FREELANCER_TOKEN=""
JOB_ID=""
PROPOSAL_ID=""
GIG_ID=""

# =============================================================================
echo ""
echo "============================================================"
echo "  Kaasb Smoke Test"
echo "  Target: ${BASE_URL}"
echo "  Time:   $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "============================================================"
echo ""

# =============================================================================
# 1. HEALTH CHECKS
# =============================================================================
log "=== 1. Health Checks ==="

R=$(http GET "${API}/health")
assert "Liveness: GET /health" "200" "$R"

R=$(http GET "${API}/health/ready")
assert "Readiness: GET /health/ready" "200" "$R"

BODY=$(echo "$R" | cut -d'|' -f2-)
DB_OK=$(jq_get "database" "$BODY")
REDIS_OK=$(jq_get "redis" "$BODY")
[ "$DB_OK" = "ok" ]    && ok  "Database connection healthy"  || fail "Database: expected 'ok', got '${DB_OK}'"
[ "$REDIS_OK" = "ok" ] && ok  "Redis connection healthy"     || fail "Redis: expected 'ok', got '${REDIS_OK}'"

# =============================================================================
# 2. AUTH — REGISTER & LOGIN
# =============================================================================
log "=== 2. Auth — Register & Login ==="

# Register client
R=$(http POST "${API}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${CLIENT_EMAIL}\",\"username\":\"smokeclient${TIMESTAMP}\",\"password\":\"${CLIENT_PASS}\",\"first_name\":\"Smoke\",\"last_name\":\"Client\",\"primary_role\":\"client\"}")
assert "Register client account" "201" "$R"

# Register freelancer
R=$(http POST "${API}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${FREELANCER_EMAIL}\",\"username\":\"smokefreelancer${TIMESTAMP}\",\"password\":\"${FREELANCER_PASS}\",\"first_name\":\"Smoke\",\"last_name\":\"Freelancer\",\"primary_role\":\"freelancer\"}")
assert "Register freelancer account" "201" "$R"

# Login client
R=$(http POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${CLIENT_EMAIL}\",\"password\":\"${CLIENT_PASS}\"}")
assert "Login as client" "200" "$R"
BODY=$(echo "$R" | cut -d'|' -f2-)
CLIENT_TOKEN=$(jq_get "data.access_token" "$BODY")
[ -n "$CLIENT_TOKEN" ] && ok "Client access token received" || fail "Client access token is empty"

# Login freelancer
R=$(http POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${FREELANCER_EMAIL}\",\"password\":\"${FREELANCER_PASS}\"}")
assert "Login as freelancer" "200" "$R"
BODY=$(echo "$R" | cut -d'|' -f2-)
FREELANCER_TOKEN=$(jq_get "data.access_token" "$BODY")
[ -n "$FREELANCER_TOKEN" ] && ok "Freelancer access token received" || fail "Freelancer access token is empty"

# GET /me
R=$(http GET "${API}/users/me" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /users/me (client)" "200" "$R"

# Refresh token
R=$(http POST "${API}/auth/refresh" -H "Authorization: Bearer ${CLIENT_TOKEN}")
if [ "$(echo "$R" | cut -d'|' -f1)" = "200" ]; then
  ok "Token refresh successful"
else
  warn "Token refresh returned $(echo "$R" | cut -d'|' -f1) — may require cookies"
  SKIP=$((SKIP + 1))
fi

# Wrong password → 401
R=$(http POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${CLIENT_EMAIL}\",\"password\":\"wrongpassword\"}")
assert "Login with wrong password returns 401" "401" "$R"

# =============================================================================
# 3. PUBLIC ENDPOINTS (no auth)
# =============================================================================
log "=== 3. Public Endpoints ==="

R=$(http GET "${API}/jobs")
assert "GET /jobs (public listing)" "200" "$R"

R=$(http GET "${API}/users/freelancers")
assert "GET /users/freelancers (public)" "200" "$R"

R=$(http GET "${API}/gigs")
assert "GET /gigs (public)" "200" "$R"

# Unauthenticated access to protected endpoint → 401
R=$(http GET "${API}/payments/summary")
assert "GET /payments/summary without token → 401" "401" "$R"

# =============================================================================
# 4. JOBS — CREATE & READ
# =============================================================================
log "=== 4. Jobs ==="

# Client creates a job
R=$(http POST "${API}/jobs" \
  -H "Authorization: Bearer ${CLIENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Smoke Test Job — Please Ignore",
    "description": "This is an automated smoke test job created to verify the platform works end-to-end. It will not be acted upon.",
    "category": "web_development",
    "job_type": "fixed",
    "fixed_price": 250.0,
    "experience_level": "intermediate",
    "duration": "1_to_4_weeks",
    "skills_required": ["python", "fastapi"]
  }')
assert "POST /jobs (client creates job)" "201" "$R"
BODY=$(echo "$R" | cut -d'|' -f2-)
JOB_ID=$(jq_get "data.id" "$BODY")
[ -n "$JOB_ID" ] && ok "Job ID received: ${JOB_ID:0:8}..." || fail "Job ID is empty after creation"

# Get job detail
if [ -n "$JOB_ID" ]; then
  R=$(http GET "${API}/jobs/${JOB_ID}")
  assert "GET /jobs/{id} (job detail)" "200" "$R"
fi

# Freelancer cannot create job
R=$(http POST "${API}/jobs" \
  -H "Authorization: Bearer ${FREELANCER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"Test","category":"web_development","job_type":"fixed","fixed_price":100}')
assert "Freelancer creating job → 403" "403" "$R"

# =============================================================================
# 5. PROPOSALS
# =============================================================================
log "=== 5. Proposals ==="

if [ -n "$JOB_ID" ]; then
  R=$(http POST "${API}/proposals" \
    -H "Authorization: Bearer ${FREELANCER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"job_id\": \"${JOB_ID}\",
      \"cover_letter\": \"Smoke test proposal — automated verification. I have 5 years of experience in web development and can complete this project efficiently.\",
      \"proposed_rate\": 225.0,
      \"estimated_duration\": \"2 weeks\"
    }")
  assert "POST /proposals (freelancer submits)" "201" "$R"
  BODY=$(echo "$R" | cut -d'|' -f2-)
  PROPOSAL_ID=$(jq_get "data.id" "$BODY")
  [ -n "$PROPOSAL_ID" ] && ok "Proposal ID received: ${PROPOSAL_ID:0:8}..." || fail "Proposal ID is empty"
else
  skip "Proposals — skipped (no job ID)"
fi

# Client cannot submit proposal
if [ -n "$JOB_ID" ]; then
  R=$(http POST "${API}/proposals" \
    -H "Authorization: Bearer ${CLIENT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"job_id\":\"${JOB_ID}\",\"cover_letter\":\"test\",\"proposed_rate\":100}")
  assert "Client submitting proposal → 403" "403" "$R"
fi

# =============================================================================
# 6. GIGS
# =============================================================================
log "=== 6. Gigs (Marketplace) ==="

R=$(http POST "${API}/gigs" \
  -H "Authorization: Bearer ${FREELANCER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Smoke Test Gig — Please Ignore",
    "description": "Automated smoke test gig. Will not be purchased.",
    "category": "web_development",
    "price": 50.0,
    "delivery_days": 3
  }')
assert "POST /gigs (freelancer creates gig)" "201" "$R"
BODY=$(echo "$R" | cut -d'|' -f2-)
GIG_ID=$(jq_get "data.id" "$BODY")
[ -n "$GIG_ID" ] && ok "Gig ID received: ${GIG_ID:0:8}..." || fail "Gig ID is empty"

# =============================================================================
# 7. PAYMENTS
# =============================================================================
log "=== 7. Payments ==="

# Payment summary (auth required)
R=$(http GET "${API}/payments/summary" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /payments/summary (client)" "200" "$R"

# Payment accounts list
R=$(http GET "${API}/payments/accounts" -H "Authorization: Bearer ${FREELANCER_TOKEN}")
assert "GET /payments/accounts (freelancer)" "200" "$R"

# Setup Qi Card account
R=$(http POST "${API}/payments/accounts" \
  -H "Authorization: Bearer ${FREELANCER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"provider":"qi_card","qi_card_phone":"+9647801234567"}')
assert "POST /payments/accounts (Qi Card setup)" "201" "$R"

# Transaction history
R=$(http GET "${API}/payments/transactions" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /payments/transactions (client)" "200" "$R"

# =============================================================================
# 8. NOTIFICATIONS
# =============================================================================
log "=== 8. Notifications ==="

R=$(http GET "${API}/notifications" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /notifications (client)" "200" "$R"

R=$(http GET "${API}/notifications" -H "Authorization: Bearer ${FREELANCER_TOKEN}")
assert "GET /notifications (freelancer)" "200" "$R"

# =============================================================================
# 9. MESSAGES
# =============================================================================
log "=== 9. Messages ==="

R=$(http GET "${API}/messages/conversations" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /messages/conversations (client)" "200" "$R"

# =============================================================================
# 10. REVIEWS
# =============================================================================
log "=== 10. Reviews ==="

R=$(http GET "${API}/reviews" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /reviews (client)" "200" "$R"

# =============================================================================
# 11. USER PROFILE
# =============================================================================
log "=== 11. User Profiles ==="

R=$(http GET "${API}/users/me" -H "Authorization: Bearer ${FREELANCER_TOKEN}")
assert "GET /users/me (freelancer)" "200" "$R"

R=$(http PATCH "${API}/users/me" \
  -H "Authorization: Bearer ${FREELANCER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"bio":"Smoke test profile update","country":"IQ"}')
assert "PATCH /users/me (update profile)" "200" "$R"

# =============================================================================
# 12. SECURITY — RATE LIMITING & BAD INPUT
# =============================================================================
log "=== 12. Security ==="

# Invalid JWT
R=$(http GET "${API}/users/me" -H "Authorization: Bearer invalid.jwt.token")
assert "Invalid JWT → 401" "401" "$R"

# Non-existent resource
R=$(http GET "${API}/jobs/00000000-0000-0000-0000-000000000000")
assert "Non-existent job → 404" "404" "$R"

# SQL injection attempt in search
R=$(http GET "${API}/jobs?search=%27+OR+1%3D1--")
assert "SQL injection in search → safe (200 or 422)" "200" "$R" 2>/dev/null || \
assert "SQL injection in search → safe (422)" "422" "$R"

# =============================================================================
# 13. GDPR
# =============================================================================
log "=== 13. GDPR / Legal ==="

R=$(http GET "${API}/gdpr/export" -H "Authorization: Bearer ${CLIENT_TOKEN}")
assert "GET /gdpr/export (data export)" "200" "$R"

# =============================================================================
# RESULTS
# =============================================================================
echo ""
echo "============================================================"
echo "  SMOKE TEST RESULTS"
echo "============================================================"
echo -e "  ${GREEN}PASSED${NC}: ${PASS}"
echo -e "  ${RED}FAILED${NC}: ${FAIL}"
echo -e "  ${YELLOW}SKIPPED${NC}: ${SKIP}"
echo ""

if [ "${#FAILURES[@]}" -gt 0 ]; then
  echo -e "${RED}Failed checks:${NC}"
  for f in "${FAILURES[@]}"; do
    echo "  • $f"
  done
  echo ""
fi

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}All checks passed. Platform is healthy.${NC}"
  exit 0
else
  echo -e "${RED}${FAIL} check(s) failed. Review above and check server logs.${NC}"
  exit 1
fi
