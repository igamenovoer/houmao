## Why

`houmao-mgr agents launch` currently advertises a local interactive mode when `--headless` is omitted, but the implementation still selects the headless backend and only attaches the operator to a tmux session whose pane returns to an idle shell. The same launch path also drops recipe `launch_policy.operator_prompt_mode`, so recipes that request unattended startup are rebuilt as interactive/default launches.

## What Changes

- Preserve recipe `launch_policy.operator_prompt_mode` when `houmao-mgr agents launch` builds a brain manifest from a native launch target.
- Change local non-`--headless` launch so it starts a real tmux-backed terminal UI session for the selected provider instead of reusing the one-shot headless turn runner.
- Keep `--headless` behavior on the existing detached headless backends.
- Persist and surface local interactive-launch session metadata so the resulting managed agent remains discoverable and controllable through the existing registry/runtime flows.
- Add regression coverage for no-server interactive launch and launch-policy propagation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-launch`: local `agents launch` must preserve recipe launch policy and distinguish detached headless launch from real tmux-backed interactive launch.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/agents/core.py`, runtime backend selection and local interactive session startup under `src/houmao/agents/realm_controller/`, plus related tmux/runtime helpers.
- Affected behavior: no-server `houmao-mgr agents launch` for Claude/Codex/Gemini, especially non-`--headless` launches.
- Test impact: new integration/runtime coverage for interactive tmux launch semantics and manifest launch-policy preservation.
