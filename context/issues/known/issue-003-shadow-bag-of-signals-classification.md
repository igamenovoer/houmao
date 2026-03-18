# Issue 003: Bag-of-Signals TUI Classification — Historical Output Pollutes Current State

## Priority
P1 — Historical signals in the tail window cause misclassification of current TUI state.

## Status
Known.

## Review Reference
Code review sections: 2.1, 3.1, 4.1, 4.2

## Summary

The shadow parser classifies TUI state by testing for regex pattern *presence* anywhere in the last 100 lines of scrollback. It treats the tail as an unordered bag of boolean flags (`has_idle_prompt`, `has_processing`, `has_response_marker`, `operator_blocked_excerpt`, etc.) and resolves conflicts via a priority-ordered if/elif chain in `_classify_surface_axes()`.

This causes state confusion when multiple signals co-exist in the tail window:

- A **response marker** (`●`) and an **idle prompt** (`❯`) can both be visible. The priority chain doesn't account for their temporal ordering within the scrollback.
- A **slash command** in scrollback history (`/model`) combined with a current idle prompt creates a false `slash_command` ui_context.
- **Processing spinner** detection (`[✶✢✽✻·✳].*…`) can false-positive on response text containing Unicode symbols followed by an ellipsis.
- `_active_prompt_payload()` scans backwards from the last non-empty line but is fragile — blank lines or status lines after the prompt can shift what counts as "last."

## Root Cause

The parser has no model of "which line is the current prompt line" vs. "which lines are historical output." It tests for signal presence anywhere in the tail, not relative to the active cursor position.

## Affected Code

- `src/houmao/agents/realm_controller/backends/claude_code_shadow.py` — `_build_surface_assessment()`, `_detect_output_variant()`, `_classify_surface_axes()`, `_active_prompt_payload()`, `_operator_blocked_excerpt()`
- `src/houmao/agents/realm_controller/backends/codex_shadow.py` — equivalent methods

## Fix Direction

### A. Separate signal extraction from state decision (4.1)

Split `_build_surface_assessment()` into:
1. **Signal Extractor** — Pure function producing a typed `SnapshotSignalSet` from one snapshot. No state decisions.
2. **State decision** moves into the Rx temporal pipeline (issue-002).

### B. Cursor-anchored prompt detection (4.2)

Replace bag-of-signals scanning with positional detection:

1. Identify the last non-blank line in the scrollback.
2. If it matches an idle prompt pattern → that's the active prompt. Everything above is historical.
3. If it matches a processing spinner → tool is working. Active zone is the spinner + preceding response text.
4. If it matches a menu/approval pattern → tool is blocked. Active zone is the menu block.
5. If none match → unknown.

Define a `prompt_boundary_index` per snapshot, partition into `historical_zone` and `active_zone`. State classification inspects only the active zone. The dialog projector can still operate on the full scrollback.

## Connections

- Amplified by issue-004 (fresh-environment TUI noise adds extra signals above the active prompt)
- The signal extractor output feeds into the Rx pipeline from issue-002
- The cursor-anchored approach also fixes 3.1 (`_active_prompt_payload()` fragility) since prompt detection becomes the primary classification mechanism rather than a secondary check
