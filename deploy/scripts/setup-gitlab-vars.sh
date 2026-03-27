#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Setup GitLab CI/CD variables for app-cde-dev-01
# Uses environment-scoped variables (same name, different env)
#
# Prerequisites:
#   - glab CLI installed and authenticated
#   - OpenSSL for JWT secret generation
#
# Usage:
#   ./deploy/scripts/setup-gitlab-vars.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Check prerequisites ──
if ! command -v glab &> /dev/null; then
    echo -e "${RED}ERROR: glab CLI not found. Install with: brew install glab${NC}"
    exit 1
fi

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  GitLab CI/CD Variable Setup — app-cde-dev-01${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# ── Helper: create/update a variable ──
set_var() {
    local NAME="$1"
    local VALUE="$2"
    local SCOPE="${3:-*}"  # * = all environments
    local MASKED="${4:-false}"
    local PROTECTED="${5:-false}"

    local SCOPE_ARG=""
    local SCOPE_LABEL="all"
    if [ "$SCOPE" != "*" ]; then
        SCOPE_ARG="--scope $SCOPE"
        SCOPE_LABEL="$SCOPE"
    fi

    local MASK_ARG=""
    [ "$MASKED" = "true" ] && MASK_ARG="--masked"

    local PROTECT_ARG=""
    [ "$PROTECTED" = "true" ] && PROTECT_ARG="--protected"

    # Try update first, create if not exists
    if glab variable update "$NAME" --value "$VALUE" $SCOPE_ARG $MASK_ARG $PROTECT_ARG 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $NAME [$SCOPE_LABEL] (updated)"
    elif glab variable set "$NAME" --value "$VALUE" $SCOPE_ARG $MASK_ARG $PROTECT_ARG 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $NAME [$SCOPE_LABEL] (created)"
    else
        echo -e "  ${RED}✗${NC} $NAME [$SCOPE_LABEL] (FAILED)"
    fi
}

# ═══════════════════════════════════════════════════
# 1. GLOBAL VARIABLES (all environments)
# ═══════════════════════════════════════════════════
echo -e "${YELLOW}▸ Global variables${NC}"

# JWT Secret (shared across all envs — generate if needed)
JWT_SECRET=$(openssl rand -hex 64)
set_var "JWT_SECRET_KEY" "$JWT_SECRET" "*" "true"
echo -e "  ${CYAN}ℹ JWT_SECRET_KEY generated with openssl rand -hex 64${NC}"

# ═══════════════════════════════════════════════════
# 2. PER-ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════

for ENV in dev staging prod; do
    echo ""
    echo -e "${YELLOW}▸ Environment: ${ENV}${NC}"

    # ── Ingress URL ──
    case "$ENV" in
        dev)     INGRESS="https://app-cde-dev-01.dev.thesmartcrew.com" ;;
        staging) INGRESS="https://app-cde-dev-01.staging.thesmartcrew.com" ;;
        prod)    INGRESS="https://cde.croo.io" ;;
    esac
    set_var "INGRESS_URL" "$INGRESS" "$ENV"

    # ── Database ──
    echo -e "  ${CYAN}ℹ Database variables — fill in actual values after creation${NC}"
    set_var "DATABASE_HOST"     "CHANGE_ME" "$ENV" "false"
    set_var "DATABASE_PORT"     "5432"      "$ENV" "false"
    set_var "DATABASE_NAME"     "croo_digital_experience" "$ENV" "false"
    set_var "DATABASE_USER"     "CHANGE_ME" "$ENV" "true"
    set_var "DATABASE_PASSWORD" "CHANGE_ME" "$ENV" "true"

    # ── Admin credentials ──
    set_var "ADMIN_USERNAME" "admin@croo.digital" "$ENV" "false"
    set_var "ADMIN_PASSWORD" "CHANGE_ME"          "$ENV" "true"

    # ── TLS Certificate ──
    echo -e "  ${CYAN}ℹ TLS variables — paste base64-encoded cert/key after creation${NC}"
    set_var "TLS_CERT" "CHANGE_ME" "$ENV" "false"
    set_var "TLS_KEY"  "CHANGE_ME" "$ENV" "true"

    # ── Observability ──
    set_var "OTLP_URL" "" "$ENV" "false"

    # ── API Keys (same across envs or env-specific) ──
    set_var "GROQ_API_KEY"      "" "$ENV" "true"
    set_var "DASHSCOPE_API_KEY" "" "$ENV" "true"
    set_var "OPENROUTER_API_KEY" "" "$ENV" "true"
    set_var "HUNTER_API_KEY"    "" "$ENV" "true"
    set_var "SERPER_API_KEY"    "" "$ENV" "true"
    set_var "WEBHOOK_API_KEY"   "" "$ENV" "true"
    set_var "MS365_CLIENT_ID"     "" "$ENV" "true"
    set_var "MS365_CLIENT_SECRET" "" "$ENV" "true"
    set_var "MS365_TENANT_ID"     "" "$ENV" "false"
    set_var "MS365_REDIRECT_URI"  "" "$ENV" "false"
    set_var "MS365_WEBHOOK_HOST"  "" "$ENV" "false"
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠ IMPORTANT: Update these placeholder values in GitLab:${NC}"
echo "  - DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD (per env)"
echo "  - ADMIN_PASSWORD (per env)"
echo "  - TLS_CERT, TLS_KEY (per env — base64 encoded)"
echo "  - API keys as needed"
echo ""
echo -e "${CYAN}ℹ CROO_KUBECONFIG is already set at the system level.${NC}"
echo -e "${CYAN}ℹ All variables are scoped to their environment in GitLab.${NC}"
echo -e "${CYAN}ℹ Same variable name is used across envs — GitLab resolves by env scope.${NC}"
