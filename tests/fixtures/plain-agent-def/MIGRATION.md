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
- `brains/api-creds/<tool>/<profile>/...` became `tools/<tool>/auth/<auth>/...` for populated plain-direct-dir roots, while reusable native bundles live in the external XDG auth store
- `brains/brain-recipes/<tool>/<name>.yaml` became `presets/<role>-<tool>-<setup>.yaml`
- preset identity is now filename-derived, and tracked preset YAML carries explicit `role`, `tool`, and `setup` instead of `default_agent_name`
- `blueprints/` are no longer the canonical reusable launch layer
- the tracked `brains/` and `blueprints/` mirrors have been removed from the supported fixture tree

## Current Workflow

1. Put behavior in `plain-agent-def/roles/<role>/system-prompt.md`.
2. Define reusable launch variants in `plain-agent-def/presets/<role>-<tool>-<setup>.yaml`.
3. Build direct native-agent homes with `houmao-mgr internals native-agent brain build --native-agent-root tests/fixtures/plain-agent-def --preset ...` or explicit `--tool --setup --auth --skill`.
4. For public managed-agent birth, use a project overlay: register the desired prompt, credential, and skills through `houmao-mgr project ...`, then launch with `houmao-mgr project agents launch --specialist <name>` or `houmao-mgr project agents launch --profile <name>`.
5. For one launched or adopted local managed agent, use scoped follow-up commands such as `houmao-mgr agents single --agent-id <id> stop`, `houmao-mgr agents single --agent-id <id> cleanup session`, or `houmao-mgr agents self ...` from inside the managed tmux session.

## Auth Notes

- Keep the tracked tree secret-free. Use [the fixture helper](../../../scripts/agents/test-fixtures/README.md) for explicit API configuration or deliberate native discovery/import.
- Credential-bearing state lives outside the checkout. Each run receives copies of only the selected credential files and setup.
- Reusable presets no longer choose personal auth bundles. Pass an explicit credential selection in a prepared external tree.
- The fixed Codex provider setup is replaced by `api-compatible`; corresponding presets use that name. Its Responses endpoint must be supplied explicitly.
- Historical sanitized usage evidence retains its original model/version facts.
