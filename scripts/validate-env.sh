#!/usr/bin/env bash
# =============================================================================
# Kaasb Platform — Environment Validation Script
# =============================================================================
# Fail fast if any required production variable is missing or has a placeholder.
# Usage: bash scripts/validate-env.sh [.env.production]
# =============================================================================

set -euo pipefail

ENV_FILE="${1:-.env.production}"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

ERRORS=0
WARNINGS=0

check() {
    local var="$1"
    local required="${2:-true}"
    local description="${3:-}"
    local val="${!var:-}"

    if [ -z "$val" ]; then
        if [ "$required" = "true" ]; then
            echo -e "${RED}FAIL${NC}  $var is empty  ${description:+(${description})}"
            ERRORS=$(( ERRORS + 1 ))
        else
            echo -e "${YELLOW}SKIP${NC}  $var is empty (optional)  ${description:+(${description})}"
            WARNINGS=$(( WARNINGS + 1 ))
        fi
        return
    fi

    # Check for placeholder values
    # Check for placeholder values. Exclude EMAIL_FROM which legitimately contains <email>.
    if [ "$var" != "EMAIL_FROM" ] && echo "$val" | grep -qiE 'CHANGE_ME|YOUR_|<.*>|example\.com$|todo|placeholder|123456|password$|secret$'; then
        echo -e "${RED}FAIL${NC}  $var contains placeholder value: '${val}'"
        ERRORS=$(( ERRORS + 1 ))
        return
    fi

    echo -e "${GREEN}OK${NC}    $var"
}

echo "============================================"
echo "  Kaasb Environment Validation"
echo "  File: $ENV_FILE"
echo "============================================"

[ -f "$ENV_FILE" ] || { echo -e "${RED}ERROR: $ENV_FILE not found${NC}"; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo ""
echo "--- Core ---"
check "DOMAIN"          true  "Production domain e.g. kaasb.com"
check "SECRET_KEY"      true  "JWT secret key (generate: openssl rand -hex 32)"
check "APP_NAME"        false "Application name"

echo ""
echo "--- Database ---"
check "DB_USER"         true
check "DB_PASSWORD"     true  "Strong password required"
check "DB_NAME"         true

echo ""
echo "--- Redis ---"
check "REDIS_PASSWORD"  true  "Redis auth password (generate: openssl rand -hex 24)"

echo ""
echo "--- Server ---"
check "WEB_CONCURRENCY" false "Gunicorn workers (default: 5)"

echo ""
echo "--- Qi Card Payment ---"
check "QI_CARD_MERCHANT_ID" false "Required for real Qi Card payments"
check "QI_CARD_SECRET_KEY"  false "Required for real Qi Card payments"
check "QI_CARD_SANDBOX"     false "Should be 'false' in production"

# Warn if sandbox is true in production
if [ "${QI_CARD_SANDBOX:-true}" = "true" ]; then
    echo -e "${YELLOW}WARN${NC}  QI_CARD_SANDBOX=true — Qi Card payments in sandbox mode"
    WARNINGS=$(( WARNINGS + 1 ))
fi

echo ""
echo "--- Email / Resend (required for email verification + password reset) ---"
check "RESEND_API_KEY"  true  "Get at: resend.com/api-keys — free tier: 3k emails/month"
check "EMAIL_FROM"      false "Default: Kaasb <noreply@kaasb.com>"
check "FRONTEND_URL"    true  "e.g. https://kaasb.com — used in email links"

echo ""
echo "--- SECRET_KEY Strength ---"
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo -e "${RED}FAIL${NC}  SECRET_KEY is too short (${#SECRET_KEY} chars, need ≥ 64)"
    ERRORS=$(( ERRORS + 1 ))
else
    echo -e "${GREEN}OK${NC}    SECRET_KEY length: ${#SECRET_KEY} chars"
fi

echo ""
echo "============================================"
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}FAILED: ${ERRORS} error(s), ${WARNINGS} warning(s)${NC}"
    echo "Fix all errors before deploying to production."
    exit 1
elif [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}PASSED with ${WARNINGS} warning(s) — review above${NC}"
    exit 0
else
    echo -e "${GREEN}ALL CHECKS PASSED — ready for production${NC}"
    exit 0
fi
