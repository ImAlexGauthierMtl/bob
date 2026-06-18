#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/frontend"

if [ -f "playwright.config.ts" ] || [ -f "playwright.config.js" ]; then
  exec npx playwright test "$@"
fi

echo "No Playwright configuration found under frontend/."
echo "Add frontend/e2e/ and playwright.config.ts before using this wrapper."
exit 1
