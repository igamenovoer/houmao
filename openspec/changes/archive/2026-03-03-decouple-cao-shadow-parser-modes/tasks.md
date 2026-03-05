## Implementation Order

These task groups are intended to be implemented in order: 1 -> 2 -> 3 -> 4 -> 5.

Tests in group 5 should be written alongside the corresponding implementation when practical, and finalized after group 4 is integrated.

## 1. Parsing Mode Contract and Session State

- [x] 1.1 Add a CAO parsing-mode contract (`cao_only` | `shadow_only`) to runtime models and launch/session inputs, with config-driven resolution and tool defaults (`claude -> shadow_only`, `codex -> cao_only`).
- [x] 1.2 Revise CAO session manifest schema/boundary models to persist selected parsing mode and enforce mode consistency on resume.
- [x] 1.3 Add fail-fast validation for unsupported parsing modes (reject any value other than `cao_only` or `shadow_only`). Do not treat specific `(tool, parsing_mode)` pairs as unsupported.
- [x] 1.4 Enforce no legacy manifest compatibility for this schema revision: old CAO manifests without parsing mode must fail fast with an explicit schema-version mismatch error (no migration/compatibility support).

## 2. CAO Turn Engine Refactor

- [x] 2.1 Extract current CAO-native turn flow into `CaoOnlyTurnEngine` without changing baseline behavior.
- [x] 2.2 Extract current runtime shadow turn flow into `ShadowOnlyTurnEngine` without changing baseline Claude behavior.
- [x] 2.3 Route `CaoRestSession.send_prompt()` through a parsing-mode engine selector and remove mixed-path branching from turn execution.
- [x] 2.4 Enforce strict non-mixing: mode-specific failures must not invoke the other parser family within the same turn.

## 3. Codex Shadow Parsing Support

- [x] 3.1 Implement a runtime Codex shadow parser module for `mode=full` output (baseline capture, status classification, answer extraction).
- [x] 3.2 Integrate Codex shadow parser with `ShadowOnlyTurnEngine` for `tool=codex` sessions.
- [x] 3.3 Add explicit waiting-user-answer detection/error handling for Codex shadow mode.
- [x] 3.4 Add Codex shadow output format detection/versioning (e.g., `codex_shadow_v1`) and explicit `unsupported_output_format` errors on mismatch (no best-effort extraction, no fallback to `cao_only`).

## 4. Output Normalization and Observability

- [x] 4.1 Add shared parser-agnostic post-processing that always runs regardless of parsing mode and provides a stable runtime contract (canonicalize status/provenance and record raw backend values; do not sanitize/rewrite extracted answer text).
- [x] 4.2 Add turn event provenance payload fields (parsing mode, parser family, output source mode, raw backend status, canonical runtime status, parser preset/format metadata where applicable, mode-specific diagnostics).
- [x] 4.3 Update runtime documentation for configuration-based parsing-mode resolution, per-tool defaults, strict no-fallback behavior, and operational guidance on non-default tool/mode selections (for example discouraging `claude + cao_only` for current upstream versions).
- [x] 4.4 Add explicit guardrails documenting that parsing mode MUST NOT alter AGENTSYS identity naming, tmux manifest-pointer publication, or name-based resolution semantics.
- [x] 4.5 Include resolved `parsing_mode` in `start-session` CLI output for CAO-backed sessions (alongside agent identity).

## 5. Validation and Regression Tests

- [x] 5.1 Add unit tests for parsing-mode validation, persistence, and resume invariants.
- [x] 5.2 Add unit tests proving `cao_only` uses only CAO-native gating/extraction paths.
- [x] 5.3 Add unit tests proving `shadow_only` uses only runtime shadow gating/extraction paths.
- [x] 5.4 Add Codex shadow parser fixture tests for status/extraction edge cases, including explicit `unsupported_output_format` on unknown/changed output.
- [x] 5.5 Add regression tests for strict non-mixing behavior when mode-specific parsing fails.
- [x] 5.6 Add tests proving no cross-mode automatic retry/fallback after mode-specific failure.
- [x] 5.7 Add tests proving old CAO manifests (without parsing mode) are rejected (no legacy compatibility).
- [x] 5.8 Add regression tests proving AGENTSYS identity/tmux manifest-pointer contracts remain unchanged for both `cao_only` and `shadow_only`.
