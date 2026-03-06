#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARCHIVE_DIR="openspec/changes/archive"

cd "${REPO_ROOT}"

if ! command -v rg >/dev/null 2>&1; then
  echo "ERROR: ripgrep (rg) is required for archive audit." >&2
  exit 2
fi

errors=0

report_block() {
  local title="$1"
  local content="$2"
  if [[ -n "${content}" ]]; then
    echo "[FAIL] ${title}" >&2
    echo "${content}" >&2
    echo >&2
    errors=$((errors + 1))
  fi
}

# 1) Forbidden legacy namespace tokens.
legacy_hits="$(rg -n "agent_system_dissect" "${ARCHIVE_DIR}" -g '*.md' || true)"
report_block "legacy namespace token detected (agent_system_dissect)" "${legacy_hits}"

# 2) Forbidden absolute main-workspace paths.
abs_hits="$(rg -n "/data(/ssd1|1)/huangzhe/code/agent-system-dissect" "${ARCHIVE_DIR}" -g '*.md' || true)"
report_block "main-workspace absolute path detected" "${abs_hits}"

# 3) Stale active-change links where archived target exists.
declare -A stale_ids=()
while IFS= read -r ref; do
  [[ -z "${ref}" ]] && continue
  id="$(sed -E 's#openspec/changes/([a-z0-9][a-z0-9-]*)/#\1#' <<<"${ref}")"
  if compgen -G "openspec/changes/archive/*-${id}" >/dev/null; then
    stale_ids["${id}"]=1
  fi
done < <(rg --no-filename -o "openspec/changes/[a-z0-9][a-z0-9-]*/" "${ARCHIVE_DIR}" -g '*.md' | sort -u || true)

if (( ${#stale_ids[@]} > 0 )); then
  echo "[FAIL] stale active-change links detected" >&2
  for id in "${!stale_ids[@]}"; do
    rg -n "openspec/changes/${id}/" "${ARCHIVE_DIR}" -g '*.md' >&2 || true
  done
  echo >&2
  errors=$((errors + 1))
fi

# 4) Normalized local references must resolve.
mapfile -t context_refs < <(rg --no-filename -o "context/[A-Za-z0-9_./-]+\.md" "${ARCHIVE_DIR}" -g '*.md' | sort -u || true)
mapfile -t archive_refs < <(rg --no-filename -o "openspec/changes/archive/[A-Za-z0-9_./-]+" "${ARCHIVE_DIR}" -g '*.md' | sort -u || true)

missing_refs=()
for ref in "${context_refs[@]}" "${archive_refs[@]}"; do
  [[ -z "${ref}" ]] && continue
  path="${ref%%:[0-9]*}"
  path="$(sed -E 's/[),.;]+$//' <<<"${path}")"
  if [[ ! -e "${path}" ]]; then
    missing_refs+=("${ref} -> ${path}")
  fi
done

if (( ${#missing_refs[@]} > 0 )); then
  echo "[FAIL] unresolved normalized local references detected" >&2
  printf '%s\n' "${missing_refs[@]}" >&2
  echo >&2
  errors=$((errors + 1))
fi

if (( errors > 0 )); then
  echo "Archive history hygiene audit FAILED (${errors} failing check group(s))." >&2
  exit 1
fi

echo "Archive history hygiene audit passed."
