## 1. Preserve Launch Policy During Local Build

- [x] 1.1 Update `houmao-mgr agents launch` to pass recipe `operator_prompt_mode` into `BuildRequest` so recipe launch policy survives local brain construction.
- [x] 1.2 Add regression coverage that a recipe-backed `agents launch` build records `launch_policy.operator_prompt_mode` in the built manifest.

## 2. Add A Real Local Interactive Launch Surface

- [x] 2.1 Extend runtime/launch-plan backend enums, schema validation, and launch-overrides resolution to support a local interactive raw-launch surface distinct from the detached headless backends.
- [x] 2.2 Implement the local interactive tmux-backed runtime session that starts the provider's persistent terminal UI, preserves role injection, and records resumable backend state.
- [x] 2.3 Update `houmao-mgr agents launch` backend selection so `--headless` keeps the current headless backends while non-`--headless` uses the new local interactive launch surface and attaches to tmux only after provider startup succeeds.

## 3. Keep Managed-Agent Flows Working For Local TUI Sessions

- [x] 3.1 Update local managed-agent identity/state/control handling so the new backend is classified as TUI transport and supports prompt, interrupt, and stop through the local runtime controller.
- [x] 3.2 Add no-server integration/runtime coverage that non-`--headless` Claude launch reaches a live provider TUI instead of an idle shell, while `--headless` continues to use the detached headless runtime path.
