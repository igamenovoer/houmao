## Why

The shadow parser classifies TUI state by testing for regex pattern *presence* anywhere in the last 100 lines of scrollback, treating the tail as an unordered bag of boolean flags and resolving conflicts via a priority-ordered if/elif chain. This causes misclassification when multiple signals co-exist in the tail window: historical response markers pollute current idle state, old slash commands create false `slash_command` ui_context, and processing spinner patterns false-positive on Unicode response text. The existing specs already require active-surface-only classification (e.g., `versioned-shadow-parser-stack` demands that historical slash-command echoes SHALL NOT keep a newer normal prompt classified as `slash_command`), but the implementation does not deliver this because it has no concept of "which line is the current prompt" vs. "which lines are historical output."

## What Changes

- **Introduce cursor-anchored zone partitioning**: Replace the bag-of-signals scanning model with a positional detection scheme that identifies the `prompt_boundary_index` in each tail snapshot — the line that separates historical output from the active prompt zone. State classification operates only on the active zone.
- **Extract a typed `SnapshotSignalSet`**: Factor the boolean signal flags out of `_build_surface_assessment()` into a pure, testable signal-extraction function that produces a typed value object. This separates signal extraction from state decision-making.
- **Refactor `_classify_surface_axes()` to consume zone-partitioned signals**: The if/elif priority chain is replaced by logic that inspects only active-zone signals, eliminating temporal confusion from historical output.
- **Fix `_active_prompt_payload()` fragility**: Prompt detection becomes the primary classification mechanism anchored to the prompt boundary, rather than a fragile backwards scan from the last non-empty line.
- **Apply equivalently to both Claude and Codex parsers**: Both `claude_code_shadow.py` and `codex_shadow.py` receive the same architectural fix.

## Capabilities

### New Capabilities
- `cursor-anchored-signal-extraction`: Defines the zone-partitioning model (prompt boundary detection, historical/active zone split) and the typed `SnapshotSignalSet` value object that replaces the current unordered boolean evidence tuple.

### Modified Capabilities
- `cao-claude-code-output-extraction`: Add requirement that shadow status classification SHALL operate on the active zone (lines at and below the prompt boundary) rather than the full bounded tail window. Historical signals above the prompt boundary SHALL NOT contribute to state classification.
- `cao-codex-output-extraction`: Same active-zone classification requirement for Codex.

## Impact

- **Code**: `claude_code_shadow.py` and `codex_shadow.py` — `_build_surface_assessment()`, `_detect_output_variant()`, `_classify_surface_axes()`, `_active_prompt_payload()`, `_operator_blocked_excerpt()` all change.
- **Data models**: New `SnapshotSignalSet` frozen dataclass in `shadow_parser_core.py`. `SurfaceAssessment` may gain a `prompt_boundary_index` or equivalent in parser metadata for diagnostics.
- **Rx pipeline**: `cao_rx_monitor.py` is not directly changed — it consumes `SurfaceAssessment` which retains the same external contract. The fix is internal to the parsers.
- **Tests**: Existing unit tests for shadow classification need updating to reflect zone-aware behavior. New test cases for the specific misclassification scenarios (historical response marker + idle prompt, old slash command + fresh prompt, spinner false-positive).
- **No breaking API changes**: The `SurfaceAssessment` external contract (availability, business_state, input_mode, ui_context) is unchanged. Consumers see more accurate classifications, not different fields.
