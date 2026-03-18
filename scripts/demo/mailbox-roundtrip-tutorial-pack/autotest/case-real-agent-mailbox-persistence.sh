#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers/common.sh
source "$SCRIPT_DIR/helpers/common.sh"

autotest_execute_roundtrip_case "mailbox-persistence"
