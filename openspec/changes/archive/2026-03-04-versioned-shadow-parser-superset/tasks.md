## 1. Shadow Parser Core + Registry

- [x] 1.1 Add a provider-agnostic shadow parser contract (status + extraction + diagnostics metadata) and baseline model.
- [x] 1.2 Implement shared output normalization utilities (ANSI stripping, NBSP handling, line normalization) for shadow parsing.
- [x] 1.3 Implement a preset registry + version-aware dispatch (env override, banner detection, deterministic fallback).
- [x] 1.4 Define anomaly codes and a structured way to attach anomalies to parser results (for example “unknown version floor used”, “unsupported output format”, “baseline invalidated”).
- [x] 1.5 Add a shared diagnostics helper to produce ANSI-stripped tail excerpts used in explicit errors.

## 2. Claude Code Shadow Parsing (Versioned + Explicit Drift)

- [x] 2.1 Refactor Claude Code shadow parsing into versioned presets registered in the new shadow parser registry.
- [x] 2.2 Add an explicit Claude Code output-format probe that fails with `unsupported_output_format`-class errors when no supported variant matches.
- [x] 2.3 Surface version-floor selection as explicit anomaly metadata (banner version differs from selected preset).
- [x] 2.4 Update runtime CAO shadow-only integration to use the new Claude Code stack entrypoint and return enriched parser metadata.
- [x] 2.5 Extend unit tests with fixture cases that assert:
  - exact preset match,
  - floor preset + anomaly,
  - drifted output -> explicit unsupported-output-format failure (no timeout).

## 3. Codex Shadow Parsing (CAO-Superset + Variants)

- [x] 3.1 Inventory Codex output variants we must support (label-style fixtures, TUI-style bullet markers, prompt/footer chrome, approvals/menus).
- [x] 3.2 Implement Codex versioned presets + probes in the registry (do not require a semver banner to match supported formats).
- [x] 3.3 Ensure Codex status classification and extraction are baseline-aware across variants.
- [x] 3.4 Implement explicit waiting-user-answer detection for approvals (`Approve ... [y/n]`, trust prompts, numbered option menus) and return an explicit error with an options excerpt.
- [x] 3.5 Extend unit tests with a curated fixture matrix covering:
  - label-style completed extraction,
  - TUI-style completed extraction,
  - approval/menu waiting-user-answer,
  - unknown/drifted output -> explicit unsupported-output-format failure.

## 4. Runtime Wiring + Default Preference

- [x] 4.1 Update `cao_rest` shadow-only paths to call the unified shadow parser stack for parser selection, baseline capture, status polling, and extraction.
- [x] 4.2 Ensure all shadow parser failures include actionable diagnostics (error code, variant/preset id, ANSI-stripped tail excerpt).
- [x] 4.3 Plumb shadow parser anomalies into the per-turn `parser_metadata` payload.
- [x] 4.4 Flip Codex CAO-backed default parsing mode to prefer `shadow_only` (retain explicit configuration to force `cao_only` for migration/incident response).
- [x] 4.5 Update docs (runtime reference + troubleshooting) to describe:
  - shadow parser preference/defaults,
  - version preset overrides,
  - how to capture fixtures for new upstream variants.
- [x] 4.6 Add a note that Gemini parser architecture is deferred to `context/issues/features/feat-gemini-headless-parser-architecture.md` and is out-of-scope for this change.

## 5. Manual Verification

- [x] 5.1 Run the existing CAO Codex demo under `parsing_mode=shadow_only` and verify non-empty extraction and no hangs/timeouts.
- [x] 5.2 Run the existing CAO Claude demos and verify:
  - processing/completed classification still works,
  - drift/unknown-format cases fail explicitly with excerpts.
