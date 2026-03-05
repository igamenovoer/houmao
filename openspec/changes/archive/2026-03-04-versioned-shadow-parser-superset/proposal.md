## Why

Codex and Claude Code interactive output formats drift quickly across releases, which can break status detection and answer extraction. When parsing lags behind upstream changes, the runtime can hang, misclassify turns, or return incorrect extracted text.

We need a repo-owned, version-aware shadow parser stack that is decoupled from upstream CAO parser release cadence, supports multiple version families, and surfaces unknown/drifted formats explicitly with actionable diagnostics.

Gemini remains headless-first in current runtime usage and is intentionally out-of-scope for this change beyond preserving existing behavior. A separate feature request will cover Gemini parser architecture.

## What Changes

- Introduce a first-class internal shadow parser stack for `codex` and `claude` with:
  - a generic core (normalization, baseline model, state model, diagnostics), and
  - provider/version-specific presets (regex/grammar rules and quirks) selected via version-aware dispatch.
- Ensure shadow parsing capabilities are parity-or-better vs upstream CAO provider parsers for supported versions:
  - status detection (`idle`, `processing`, `completed`, `waiting_user_answer`),
  - waiting-for-user detection (menus, approvals), and
  - answer extraction boundaries.
- Add explicit drift/unknown handling:
  - unsupported output formats are detected and reported explicitly (not treated as `processing` indefinitely),
  - unknown tool versions are detected and reported (even if a floor preset is used).
- Prefer the runtime-owned shadow parser path over CAO-native parsing after rollout.
  - `cao_only` remains available as an explicit compatibility/migration configuration.
  - **BREAKING** (behavioral default): Codex CAO-backed sessions are expected to prefer `shadow_only` by default once parity is achieved.
- Add a fixture-driven test matrix by provider and version family, including intentionally drifted fixtures that assert explicit anomaly results.
- Keep Gemini on existing headless mode only in this change (no Gemini shadow/TUI parser stack integration).

## Capabilities

### New Capabilities

- `versioned-shadow-parser-stack`: a provider-agnostic shadow parsing contract (status + extraction + anomalies) with version-aware dispatch and strong diagnostics for format drift, scoped to CAO/TUI providers in this change (`codex`, `claude`).

### Modified Capabilities

- `brain-launch-runtime`: update CAO parsing-mode defaults and runtime parser preference so shadow parsing is the preferred/default path when available.
- `cao-codex-output-extraction`: expand Codex shadow parsing to be a functional superset of CAO provider behavior across supported variants (including approvals/menus) with explicit unknown-format detection.
- `cao-claude-code-output-extraction`: strengthen Claude Code shadow parsing with explicit unknown-format detection and version-floor anomaly reporting.

## Impact

- Runtime code:
  - new shadow parser core + registry modules,
  - refactors to existing `CodexShadowParser` / `ClaudeCodeShadowParser` into versioned presets,
  - CAO backend parser selection and default parsing-mode behavior updates.
- Tests:
  - new fixture corpus and matrix tests by provider/version family,
  - drift/unknown fixtures to validate explicit anomaly reporting.
- Documentation:
  - update runtime reference docs to describe shadow parser preference, configuration overrides, and diagnostics.
