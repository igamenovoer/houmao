#!/usr/bin/env bash
set -euo pipefail

PACK_NAME="${1:?pack name is required}"
MAINTAINED_HINT="${2:-}"

echo "Archived demo \`${PACK_NAME}\` is not runnable." >&2
echo "This legacy workflow depends on the removed \`tests/fixtures/agents/\` fixture-root contract." >&2
if [[ -n "$MAINTAINED_HINT" ]]; then
  echo "Use maintained demo surfaces from \`scripts/demo/README.md\` instead, such as \`${MAINTAINED_HINT}\`." >&2
else
  echo "Use maintained demo surfaces from \`scripts/demo/README.md\` instead." >&2
fi
exit 1
