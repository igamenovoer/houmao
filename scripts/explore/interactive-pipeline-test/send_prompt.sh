#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../.." && pwd)"
cd "${repo_root}"
# Select --run-dir from fixture.py prepare; lifecycle uses the current manager.
exec pixi run python scripts/agents/test-fixtures/fixture.py prompt "$@"
