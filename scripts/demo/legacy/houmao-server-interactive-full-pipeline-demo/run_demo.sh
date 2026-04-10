#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../removed_agents_fixture_guard.sh" \
  "houmao-server-interactive-full-pipeline-demo" \
  "scripts/demo/minimal-agent-launch/"
