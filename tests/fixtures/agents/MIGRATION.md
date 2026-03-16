# Migration: Legacy Agent Homes to Runtime Homes

Migration is complete. Legacy `agents/gpu_*` profile directories have been removed.

Legacy users may still have per-agent homes under paths like:

- `agents/<agent>/homes/codex/`
- `agents/<agent>/homes/claude/`
- `agents/<agent>/homes/gemini/`

The new model builds homes under a configurable runtime root:

- `<runtime_root>/homes/<tool>/<home-id>/`
- default: `tmp/agents-runtime/homes/<tool>/<home-id>/`

## Current Workflow

1. Move prompts/behavior to `agents/roles/<role>/system-prompt.md`.
2. Define a brain recipe in `agents/brains/brain-recipes/<tool>/...`.
3. Build with `scripts/agents/build_brain_home.py`.
4. Launch via `<runtime_root>/homes/<tool>/<home-id>/launch.sh`.

## Credential Notes

- Place secrets only under `agents/brains/api-creds/<tool>/<cred-profile>/`.
- Recipes pick credential profiles by name, and blueprints inherit that choice through the selected recipe.
- Concurrent runs may reuse the same credential profile when the provider/tool allows shared API-key or token usage.
- If you need a separate rate-limit lane or the provider enforces session limits, rotate by creating a new `<cred-profile>` and updating the affected recipes/blueprints.
