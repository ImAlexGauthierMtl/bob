#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/frontend"
echo "🎨 Starting frontend on http://localhost:4200"
npm run start -- --proxy-config proxy.conf.json
