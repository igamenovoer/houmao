## Why

Houmao can already run Kimi Code in headless prompt mode, but Kimi's interactive TUI is still treated as an unsupported local interactive surface. Operators need Kimi Code TUI sessions to launch, relaunch, accept managed prompts, and report live state with the same tmux-backed workflow used for Claude Code, Codex, and Gemini.

## What Changes

- Add maintained Kimi Code support for the `local_interactive` backend.
- Recognize live Kimi TUI processes, including the observed `kimi-code` process name.
- Add Kimi provider-native relaunch mappings for latest-chat and exact-session continuation.
- Validate Kimi relaunch argument combinations against Kimi's native TUI option conflicts.
- Project launch-owned Kimi model overrides into TUI startup with `--model <alias>`.
- Suppress Kimi's interactive update preflight for managed TUI launches with the supported Kimi environment switch.
- Add Kimi visible-surface parsing for operator state, including ready, active, and approval-blocked surfaces.
- Add a versioned Kimi TUI signal profile for shared tracker reduction from raw tmux snapshots.
- Keep Kimi headless prompt-mode behavior separate from Kimi TUI behavior.
- Keep managed `--skills-dir` projection scoped to Kimi headless prompt mode unless Kimi adds a maintained TUI skills-dir surface.
- Document the Kimi TUI launch and relaunch posture in the run-phase reference.

## Capabilities

### New Capabilities

- `kimi-code-tui-support`: Kimi-specific TUI launch, prompt, interrupt, relaunch, parsing, and tracking behavior.

### Modified Capabilities

- `brain-launch-runtime`: Runtime `local_interactive` support and provider-native relaunch mappings include Kimi Code TUI.
- `agent-model-selection`: Kimi launch-owned model projection applies to Kimi TUI startup as well as prompt-mode/headless startup.
- `official-tui-state-tracking`: Official live TUI parsing and process detection support Kimi Code TUI as a maintained supported surface.
- `versioned-tui-signal-profiles`: The shared versioned TUI profile registry includes a Kimi Code TUI app/profile.
- `docs-run-phase-reference`: Run-phase documentation includes Kimi Code in local interactive backend and relaunch-continuation references.

## Impact

- Affected runtime code includes local interactive launch planning, managed launch environment projection, tmux process inspection allowlists, prompt submission and interrupt paths, relaunch argument generation, relaunch conflict validation, and Kimi model-selection argument handling.
- Affected tracking code includes the shared TUI profile registry, Kimi-specific detector profile, official parser adapter, server/gateway/passive observer diagnostics, and fixture-based parser/tracker tests.
- Affected docs include run-phase backend and relaunch reference material.
- No public Kimi headless backend rename or stored-data migration is intended.
