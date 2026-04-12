## Why

Claude specialist model selection currently persists and resolves correctly, but the local interactive TUI path can lose the projected `ANTHROPIC_MODEL` value before the provider process starts. This makes `--model sonnet`-style user preference appear ignored when the account default is Opus, and it also leaves Claude reasoning preference split between runtime-home state and process launch behavior.

## What Changes

- Project launch-owned Claude model preferences into provider CLI arguments using `claude --model <name>` for both interactive TUI and headless launches.
- Project launch-owned Claude reasoning preference into provider CLI arguments using `claude --effort <level>` for both interactive TUI and headless launches when the resolved Houmao reasoning preset maps to a Claude effort level.
- Keep existing auth-bundle/model env support for Claude baseline or imported native state, including `ANTHROPIC_MODEL` and alias pinning variables, but do not rely on projected launch-owned `ANTHROPIC_MODEL` as the primary authority for Houmao-managed Claude launch overrides.
- Preserve the existing model-selection precedence contract: copied native baseline, source default, launch-profile default, direct launch override, then runtime-only in-session mutation.
- Record provenance for generated Claude CLI model/effort arguments in the existing model-selection manifest metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-model-selection`: Change Claude launch-owned model and reasoning projection so Houmao-managed Claude TUI and headless launches pass resolved model and effort preferences through final Claude CLI arguments.

## Impact

- Affected code likely includes Claude model projection in `src/houmao/agents/brain_builder.py`, launch-plan extraction in `src/houmao/agents/realm_controller/launch_plan.py`, Claude launch command construction for local interactive and headless paths, and model-mapping policy/provenance helpers.
- Tests should cover both interactive launch command construction and headless command construction, plus manifest/provenance for `--model` and `--effort`.
- No new external dependency is required.
- No secret values should be emitted in CLI arguments; model names and effort levels are non-secret launch preferences.
