# Runtime Migration Parity Checklist

This checklist defines behavior-level parity gates for the runtime extraction.

## Required Gates

1. Unit tests pass in destination runtime suites.

```bash
pixi run python -m pytest tests/unit/agents tests/unit/cao
```

2. Runtime schema files remain parity-equivalent with source mirror.

```bash
scripts/parity/check_runtime_parity.sh
```

3. Stale namespace imports are absent in destination runtime code/tests/scripts.

```bash
rg -n -- "^(from|import) agent_system_dissect" src tests scripts
```

4. Demo workflows are runnable from destination repository layout.

```bash
scripts/demo/cao-server-launcher/run_demo.sh
scripts/demo/cao-codex-session/run_demo.sh
scripts/demo/cao-claude-session/run_demo.sh
scripts/demo/gemini-headless-session/run_demo.sh
```

5. Packaging checks pass.

```bash
pixi run python -m build --sdist --wheel
pixi run python -m twine check dist/*
```

6. Installed wheel smoke checks pass in a clean virtual environment.

```bash
python -m venv tmp/wheel-smoke
source tmp/wheel-smoke/bin/activate
pip install --upgrade pip
pip install dist/*.whl
python -c "import gig_agents; import gig_agents.agents.brain_launch_runtime"
gig-agents-cli --help
gig-cao-server --help
```

## Optional Manual Headless tmux Smoke

Use this operator workflow when `tmux` and relevant tool CLIs are available:

```bash
python tests/manual/manual_headless_tmux_smoke.py \
  --agent-def-dir tests/fixtures/agents \
  --codex-manifest <manifest-path>
```

- Repeat with `--claude-manifest` and `--gemini-manifest` when those tools are configured.
- This is optional for CI but recommended before release tagging.
