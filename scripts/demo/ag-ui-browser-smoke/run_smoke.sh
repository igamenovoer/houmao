#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMOKE_SCRIPT="$SCRIPT_DIR/browser_smoke.ts"

if ! command -v bun >/dev/null 2>&1; then
  echo "Bun is required for the AG-UI browser smoke." >&2
  exit 2
fi

if ! bun -e "import { chromium } from 'playwright'; if (!chromium) process.exit(1);" >/dev/null 2>&1; then
  echo "Bun-global Playwright is required for the AG-UI browser smoke." >&2
  exit 2
fi

exec bun "$SMOKE_SCRIPT"
