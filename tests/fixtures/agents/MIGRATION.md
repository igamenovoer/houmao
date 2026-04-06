# Migration: Simplified Agent Definition Model

The tracked fixture tree now uses the simplified source model:

1. `agents/skills/<skill>/`
2. `agents/tools/<tool>/adapter.yaml`
3. `agents/tools/<tool>/setups/<setup>/`
4. `agents/tools/<tool>/auth/<auth>/`
5. `agents/roles/<role>/system-prompt.md`
6. `agents/presets/<preset>.yaml`

## What Changed

- `brains/cli-configs/<tool>/<profile>/...` became `tools/<tool>/setups/<setup>/...`
- `brains/api-creds/<tool>/<profile>/...` became `tools/<tool>/auth/<auth>/...`
- `brains/brain-recipes/<tool>/<name>.yaml` became `presets/<role>-<tool>-<setup>.yaml`
- preset identity is now filename-derived, and tracked preset YAML carries explicit `role`, `tool`, and `setup` instead of `default_agent_name`
- `blueprints/` are no longer the canonical reusable launch layer
- the tracked `brains/` and `blueprints/` mirrors have been removed from the supported fixture tree

## Current Workflow

1. Put behavior in `agents/roles/<role>/system-prompt.md`.
2. Define reusable launch variants in `agents/presets/<role>-<tool>-<setup>.yaml`.
3. Build with `houmao-mgr brains build --preset ...` or explicit `--tool --setup --auth --skill`.
4. Launch with `houmao-mgr agents launch --agents <role> --provider <provider>`.

## Auth Notes

- Keep secrets only under `agents/tools/<tool>/auth/<auth>/`.
- Presets choose a default auth bundle by name, and operators may override it at launch time with `--auth`.
- Concurrent runs may reuse the same auth bundle when the provider/tool allows it.
- If you need a separate rate-limit lane, create a new auth bundle and update the affected preset or launch command.
