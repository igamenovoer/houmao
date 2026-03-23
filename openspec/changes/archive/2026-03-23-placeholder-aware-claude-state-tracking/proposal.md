## Why

Claude Code now renders startup and idle prompt suggestions on the visible `❯` line using styling that makes them look like editable text after ANSI is stripped. The current tracked-TUI Claude detector treats any non-empty post-prompt text as active editing, so fresh live-watch and runtime samples incorrectly report `surface.editing_input=yes` until the operator interacts with the prompt and the placeholder repaint disappears.

## What Changes

- Make Claude prompt editing detection robust to styled placeholder text so `surface.editing_input` reflects actual draft input rather than startup or idle suggestions.
- Add style-aware prompt-region interpretation for Claude detector profiles instead of relying only on ANSI-stripped prompt payload text.
- Refactor Claude prompt interpretation so version-specific prompt behavior can evolve through profile-owned variants, similar to the existing Codex prompt behavior approach, without rewriting shared tracker engine logic.
- Preserve the current public tracked-state vocabulary and reducer ownership while tightening the detector-side semantics that feed `surface.editing_input`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `official-tui-state-tracking`: `surface.editing_input` semantics for supported Claude interactive surfaces change so styled placeholder text on the visible prompt line does not count as active editing.
- `versioned-tui-signal-profiles`: supported app profiles may use style-aware, version-selectable prompt/surface-region behavior variants for Claude in addition to Codex so drift in placeholder presentation can be absorbed inside profile-owned logic.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`, `src/houmao/shared_tui_tracking/surface.py`, and new or related Claude prompt-behavior helpers under `src/houmao/shared_tui_tracking/apps/claude_code/`
- Affected tests: shared TUI tracking unit coverage for Claude prompt interpretation, startup placeholder handling, and version-family compatibility behavior
- Affected behavior: Claude live-watch, official/runtime tracking, and replay-driven state samples should report `surface.editing_input=no` for styled placeholder prompts until the user actually begins editing
