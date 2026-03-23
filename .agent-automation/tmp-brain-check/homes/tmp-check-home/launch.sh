#!/usr/bin/env bash
set -euo pipefail
export CODEX_HOME=/data1/huangzhe/code/houmao/.agent-automation/tmp-brain-check/homes/tmp-check-home
BOOTSTRAP_PYTHON=()
if command -v pixi >/dev/null 2>&1 && [[ -f /data1/huangzhe/code/houmao/pyproject.toml ]]; then
  BOOTSTRAP_PYTHON=(pixi run --manifest-path /data1/huangzhe/code/houmao/pyproject.toml python)
else
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  if [[ -z "${PYTHON_BIN}" ]]; then
    echo "launch helper requires `pixi`, `python3`, or `python` on PATH." >&2
    exit 127
  fi
  export PYTHONPATH=/data1/huangzhe/code/houmao/src${PYTHONPATH:+:${PYTHONPATH}}
  BOOTSTRAP_PYTHON=("${PYTHON_BIN}")
fi
EXTRA_ARGS=("$@")
exec "${BOOTSTRAP_PYTHON[@]}" -m houmao.agents.launch_policy.cli --tool codex --backend raw_launch --executable codex --working-directory "$PWD" --home-path /data1/huangzhe/code/houmao/.agent-automation/tmp-brain-check/homes/tmp-check-home --requested-operator-prompt-mode unattended -- "${EXTRA_ARGS[@]}"
