# Minimal Managed-Agent Launch

For contributors testing birth and transport, this demo uses one shared `minimal-launch` role with Claude Code or Codex. It prepares a fresh external private project, registers its selected API credential and specialist, and launches through `houmao-mgr project agents launch`. Follow-up operations select the returned managed identity.

## Run

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code --case cloud-api --model MODEL --env-file .env
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex --case cloud-api --model MODEL --env-file .env --headless
```

Replace `MODEL` with the explicitly qualified DeepSeek model. For a compatible self-hosted service, select `--case self-hosted` and provide its endpoint/model references. The helper's `--context-window`, `--reasoning-effort`, and capability options are available when required. Native login uses `--auth-method native-login --auth-bundle NAME` separately from API cases. See the [fixture helper](../../agents/test-fixtures/README.md) for discovery/import and protocol conventions.

The runner launches in TUI mode with unattended prompt policy by default. `--headless` selects `houmao-mgr project agents launch --mode headless`, sends [inputs/prompt.txt](inputs/prompt.txt), records the public result, and stops the captured agent. TUI leaves the owned session available for inspection. The returned `run_dir` contains private `summary.json`, `logs/prepare.json`, `logs/launch.json`, and `logs/state.json`; headless also writes `logs/stop.json`. Credentials and raw provider state stay outside the checkout. `--output-dir` selects an external parent for unique runs.

## Follow Up

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/run --live
pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir /external/run --prompt 'Reply exactly OK'
pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir /external/run
```

The helper selects the run's registry and runtime roots automatically. For direct CLI follow-up use `houmao-mgr agents single --agent-id ID state` or `stop` with those roots selected. Cleanup uses only the captured identity and preserves private evidence.
