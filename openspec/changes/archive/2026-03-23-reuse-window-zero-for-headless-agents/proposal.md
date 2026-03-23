## Why

Managed headless agents currently create a tmux session with an idle bootstrap shell in window 0 and then spawn separate `turn-N` windows for each prompt. That shape is at odds with the intended operator model: one headless agent should have one stable primary terminal surface, and attaching to the session should always show the agent itself rather than a transient per-turn window.

## What Changes

- Change tmux-backed headless runtime sessions so the agent execution surface always lives in window 0, is named `agent`, and reuses that same window for every turn.
- Disallow per-turn tmux window creation for headless agent execution and keep headless prompt execution serialized rather than overlapping in the same session.
- Replace per-turn `tmux new-window` allocation with same-pane fresh-process execution on window 0 and keep that primary surface returning to an idle agent shell between turns.
- Clarify that auxiliary session windows are allowed for supporting processes such as gateway or operator diagnostics, but they do not replace or redefine the agent’s primary window-0 surface.
- Update managed headless API and detailed-state contracts so tmux inspectability points to a stable agent surface rather than transient `turn-N` windows, using the stable window name `agent` where window metadata is exposed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: change the tmux-backed headless runtime contract so the agent owns a stable primary window-0 execution surface and turns reuse that window instead of creating per-turn windows.
- `houmao-server-agent-api`: clarify that managed headless turn execution remains single-active-turn and uses the stable headless agent surface rather than transient per-turn tmux windows.
- `managed-agent-detailed-state`: adjust headless inspectability expectations so detailed state refers to the stable agent surface and does not imply per-turn window topology.

## Impact

- Affected code includes headless runtime session bootstrap, headless turn execution, tmux control helpers, managed-headless interrupt fallback, and managed-agent inspect/report surfaces.
- Affected user-visible behavior includes attaching to headless tmux sessions, live demo watching, and any diagnostic tooling that currently assumes `turn-N` windows.
- The change preserves the existing no-concurrent-turn contract for managed headless agents, makes that serialized execution model visible in the tmux layout, and removes destructive `kill-window` assumptions against the primary agent surface.
