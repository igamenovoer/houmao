# Migration: Simplified Plain Agent-Definition Fixture Model

The maintained tracked plain-direct-dir fixture tree now lives under `tests/fixtures/plain-agent-def/` and uses the simplified source model:

1. `plain-agent-def/skills/<skill>/`
2. `plain-agent-def/tools/<tool>/adapter.yaml`
3. `plain-agent-def/tools/<tool>/setups/<setup>/`
4. `plain-agent-def/tools/<tool>/auth/<auth>/`
5. `plain-agent-def/roles/<role>/system-prompt.md`
6. `plain-agent-def/presets/<preset>.yaml`
7. `plain-agent-def/launch-profiles/<profile>.yaml`

## What Changed

- `brains/cli-configs/<tool>/<profile>/...` became `tools/<tool>/setups/<setup>/...`
- `brains/api-creds/<tool>/<profile>/...` became `tools/<tool>/auth/<auth>/...` for populated plain-direct-dir roots, while maintained host-local bundles now live under `tests/fixtures/auth-bundles/<tool>/<auth>/...`
- `brains/brain-recipes/<tool>/<name>.yaml` became `presets/<role>-<tool>-<setup>.yaml`
- preset identity is now filename-derived, and tracked preset YAML carries explicit `role`, `tool`, and `setup` instead of `default_agent_name`
- `blueprints/` are no longer the canonical reusable launch layer
- the tracked `brains/` and `blueprints/` mirrors have been removed from the supported fixture tree

## Current Workflow

1. Put behavior in `plain-agent-def/roles/<role>/system-prompt.md`.
2. Define reusable launch variants in `plain-agent-def/presets/<role>-<tool>-<setup>.yaml`.
3. Build with `houmao-mgr brains build --preset ...` or explicit `--tool --setup --auth --skill`.
4. Launch with `houmao-mgr agents launch --agents <role> --provider <provider>`.

## Auth Notes

- Keep the tracked plain fixture tree secret-free. Maintained host-local bundles now live under `tests/fixtures/auth-bundles/<tool>/<auth>/`.
- When a direct-dir workflow needs auth inside its own tree, materialize the selected bundle into `plain-agent-def/tools/<tool>/auth/<auth>/` under a copied temp root.
- Presets choose a default auth bundle by name, and operators may override it at launch time with `--auth`.
- Concurrent runs may reuse the same auth bundle when the provider/tool allows it.
- If you need a separate rate-limit lane, create a new auth bundle and update the affected preset or launch command.
