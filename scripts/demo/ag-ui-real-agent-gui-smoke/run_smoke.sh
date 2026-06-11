#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
APP_DIR="$REPO_ROOT/apps/ag-ui-workbench"

if [[ "${HMWB_REAL_AGENT_SMOKE:-}" != "1" ]]; then
  echo "Set HMWB_REAL_AGENT_SMOKE=1 to run the real-agent AG-UI GUI smoke." >&2
  exit 2
fi

if [[ -z "${HMWB_PASSIVE_SERVER_URL:-}" ]]; then
  echo "Set HMWB_PASSIVE_SERVER_URL to the passive-server base URL." >&2
  exit 2
fi

if [[ -z "${HMWB_TEST_AGENT_NAME:-}" && -z "${HMWB_TEST_AGENT_ID:-}" ]]; then
  echo "Set HMWB_TEST_AGENT_NAME or HMWB_TEST_AGENT_ID to select the existing test agent." >&2
  exit 2
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "Bun is required for the real-agent AG-UI GUI smoke." >&2
  exit 2
fi

cd "$APP_DIR"

if ! bun -e "import { chromium } from 'playwright'; if (!chromium) process.exit(1);" >/dev/null 2>&1; then
  echo "Bun-global Playwright is required for the real-agent AG-UI GUI smoke." >&2
  exit 2
fi

exec bun run e2e:real-agent-smoke
