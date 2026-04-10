#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../removed_agents_fixture_guard.sh" \
  "gateway-stalwart-cypht-interactive-demo-pack" \
  "scripts/demo/single-agent-mail-wakeup/"
