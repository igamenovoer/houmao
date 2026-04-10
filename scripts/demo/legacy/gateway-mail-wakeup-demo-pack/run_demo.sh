#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../removed_agents_fixture_guard.sh" \
  "gateway-mail-wakeup-demo-pack" \
  "scripts/demo/single-agent-gateway-wakeup-headless/"
