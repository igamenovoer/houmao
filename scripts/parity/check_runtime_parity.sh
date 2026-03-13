#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOUMAO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_REPO_ROOT="${SOURCE_REPO_ROOT:-$(cd "$HOUMAO_ROOT/../../.." && pwd)}"
SOURCE_SCHEMA_DIR="$SOURCE_REPO_ROOT/src/agent_system_dissect/agents/realm_controller/schemas"
DEST_SCHEMA_DIR="$HOUMAO_ROOT/src/houmao/agents/realm_controller/schemas"

log() {
  echo "[parity] $*"
}

fail() {
  echo "[parity] FAIL: $*" >&2
  exit 1
}

if [[ ! -d "$SOURCE_SCHEMA_DIR" ]]; then
  fail "missing source schema directory: $SOURCE_SCHEMA_DIR"
fi
if [[ ! -d "$DEST_SCHEMA_DIR" ]]; then
  fail "missing destination schema directory: $DEST_SCHEMA_DIR"
fi

log "source repo root: $SOURCE_REPO_ROOT"
log "destination root: $HOUMAO_ROOT"

log "checking schema parity"
while IFS= read -r schema; do
  name="$(basename "$schema")"
  if [[ ! -f "$DEST_SCHEMA_DIR/$name" ]]; then
    fail "missing destination schema: $name"
  fi
  if ! diff -u "$schema" "$DEST_SCHEMA_DIR/$name" >/dev/null; then
    fail "schema mismatch: $name"
  fi
done < <(find "$SOURCE_SCHEMA_DIR" -type f -name '*.json' | sort)

log "checking stale import paths"
if rg -n -- "^(from|import) agent_system_dissect" "$HOUMAO_ROOT/src" "$HOUMAO_ROOT/tests" "$HOUMAO_ROOT/scripts" >/dev/null; then
  fail "found stale agent_system_dissect imports in destination runtime paths"
fi

log "parity preflight checks passed"
