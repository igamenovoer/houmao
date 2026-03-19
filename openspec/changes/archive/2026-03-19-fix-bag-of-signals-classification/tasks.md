## 1. Core data model and shared utility

- [x] 1.1 Add a provider-neutral `SnapshotSignalSet` frozen dataclass to `shadow_parser_core.py` with zone fields, common active-zone booleans (`has_idle_prompt`, `has_processing_spinner`, `has_response_marker`, `has_operator_blocked`, `has_slash_command`, `has_error_banner`), `operator_blocked_excerpt`, `active_prompt_payload`, `anchor_type`, and generic blocked-surface metadata such as `blocked_surface_kind`
- [x] 1.2 Add shared `find_prompt_boundary(tail_lines, anchor_patterns) -> int | None` utility function to `shadow_parser_core.py` implementing the reverse-scan algorithm over provider-defined boundary anchors

## 2. Claude parser refactor

- [x] 2.1 Define Claude boundary anchors (idle prompt, spinner/progress, menu/approval, setup/trust) in `claude_code_shadow.py`, including the prompt-owning-progress rule needed to preserve `working + freeform`
- [x] 2.2 Implement `_extract_signals(tail_lines, preset) -> SnapshotSignalSet` static method in `ClaudeCodeShadowParser` using `find_prompt_boundary()` and active-zone-scoped regex detection
- [x] 2.3 Refactor `_build_surface_assessment()` to call `_extract_signals()` and pass the `SnapshotSignalSet` to `_classify_surface_axes()`
- [x] 2.4 Refactor `_classify_surface_axes()` to accept `SnapshotSignalSet` instead of boolean tuple and interpret provider-specific blocked-surface kinds without adding Claude-shaped fields to shared core types
- [x] 2.5 Remove the now-unused inline boolean flag computation and old `_active_prompt_payload()` backwards-scan method (prompt payload is now part of `SnapshotSignalSet`)

## 3. Codex parser refactor

- [x] 3.1 Define Codex boundary anchors (idle prompt, spinner/progress, approval, login/trust) in `codex_shadow.py`, including the prompt-owning-progress rule needed to preserve `working + freeform`
- [x] 3.2 Implement `_extract_signals(tail_lines, preset) -> SnapshotSignalSet` static method in `CodexShadowParser` using `find_prompt_boundary()` and active-zone-scoped regex detection
- [x] 3.3 Refactor `_build_surface_assessment()` to call `_extract_signals()` and pass the `SnapshotSignalSet` to `_classify_surface_axes()`
- [x] 3.4 Refactor `_classify_surface_axes()` to accept `SnapshotSignalSet` instead of boolean tuple and interpret provider-specific blocked-surface kinds without adding Codex-specific fields to shared core types
- [x] 3.5 Remove the now-unused inline boolean flag computation and old `_active_prompt_payload()` backwards-scan method

## 4. Tests

- [x] 4.1 Add unit tests for `find_prompt_boundary()` with various anchor patterns and edge cases (no anchor, multiple anchors, anchor at first line, anchor at last line)
- [x] 4.2 Add unit tests for Claude `_extract_signals()` verifying zone partitioning, prompt-owning-progress boundaries, and active-zone-only signal detection
- [x] 4.3 Add unit tests for Codex `_extract_signals()` verifying zone partitioning, prompt-owning-progress boundaries, and active-zone-only signal detection
- [x] 4.4 Add regression tests for the specific misclassification scenarios from issue-003: historical response marker + idle prompt, old slash command + fresh prompt, spinner false-positive on Unicode response text
- [x] 4.5 Update existing classification tests to reflect zone-aware behavior, including asserting that `prompt + spinner/progress` layouts keep the prompt line inside the active zone

## 5. Verification

- [x] 5.1 Run `pixi run test-runtime` and verify all existing tests pass with the refactored parsers
- [x] 5.2 Run `pixi run typecheck` and verify no type errors from the new dataclass and refactored method signatures
- [x] 5.3 Run `pixi run lint` and verify formatting/style compliance
