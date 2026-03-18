## 1. Core data model and shared utility

- [ ] 1.1 Add `SnapshotSignalSet` frozen dataclass to `shadow_parser_core.py` with fields: `prompt_boundary_index`, `active_zone_lines`, `historical_zone_lines`, per-signal booleans, `operator_blocked_excerpt`, `active_prompt_payload`, `anchor_type`
- [ ] 1.2 Add shared `find_prompt_boundary(tail_lines, anchor_patterns) -> int | None` utility function to `shadow_parser_core.py` implementing the reverse-scan algorithm

## 2. Claude parser refactor

- [ ] 2.1 Define Claude anchor patterns list (idle prompt, spinner, menu/approval, setup/trust) in `claude_code_shadow.py`
- [ ] 2.2 Implement `_extract_signals(tail_lines, preset) -> SnapshotSignalSet` static method in `ClaudeCodeShadowParser` using `find_prompt_boundary()` and active-zone-scoped regex detection
- [ ] 2.3 Refactor `_build_surface_assessment()` to call `_extract_signals()` and pass the `SnapshotSignalSet` to `_classify_surface_axes()`
- [ ] 2.4 Refactor `_classify_surface_axes()` to accept `SnapshotSignalSet` instead of boolean tuple
- [ ] 2.5 Remove the now-unused inline boolean flag computation and old `_active_prompt_payload()` backwards-scan method (prompt payload is now part of `SnapshotSignalSet`)

## 3. Codex parser refactor

- [ ] 3.1 Define Codex anchor patterns list (idle prompt, spinner, approval, login/trust) in `codex_shadow.py`
- [ ] 3.2 Implement `_extract_signals(tail_lines, preset) -> SnapshotSignalSet` static method in `CodexShadowParser` using `find_prompt_boundary()` and active-zone-scoped regex detection
- [ ] 3.3 Refactor `_build_surface_assessment()` to call `_extract_signals()` and pass the `SnapshotSignalSet` to `_classify_surface_axes()`
- [ ] 3.4 Refactor `_classify_surface_axes()` to accept `SnapshotSignalSet` instead of boolean tuple
- [ ] 3.5 Remove the now-unused inline boolean flag computation and old `_active_prompt_payload()` backwards-scan method

## 4. Tests

- [ ] 4.1 Add unit tests for `find_prompt_boundary()` with various anchor patterns and edge cases (no anchor, multiple anchors, anchor at first line, anchor at last line)
- [ ] 4.2 Add unit tests for Claude `_extract_signals()` verifying zone partitioning and active-zone-only signal detection
- [ ] 4.3 Add unit tests for Codex `_extract_signals()` verifying zone partitioning and active-zone-only signal detection
- [ ] 4.4 Add regression tests for the specific misclassification scenarios from issue-003: historical response marker + idle prompt, old slash command + fresh prompt, spinner false-positive on Unicode response text
- [ ] 4.5 Update existing classification tests to reflect zone-aware behavior (adjust synthetic tail lines to place signals in the correct zone)

## 5. Verification

- [ ] 5.1 Run `pixi run test-runtime` and verify all existing tests pass with the refactored parsers
- [ ] 5.2 Run `pixi run typecheck` and verify no type errors from the new dataclass and refactored method signatures
- [ ] 5.3 Run `pixi run lint` and verify formatting/style compliance
