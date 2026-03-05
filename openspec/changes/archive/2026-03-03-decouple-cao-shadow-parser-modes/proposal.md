## Why

Our CAO-backed runtime currently has asymmetric parsing behavior: Claude Code uses a runtime shadow parser, while Codex relies on CAO-native status/output parsing. This makes behavior harder to reason about, increases coupling to provider-specific CAO semantics, and makes parser fallback policy implicit instead of explicit.

## What Changes

- Introduce an explicit CAO turn `parsing_mode` with only two allowed values: `cao_only` and `shadow_only`.
- Treat parsing mode as a configuration choice with tool-specific defaults:
  - Claude agents default to `shadow_only`.
  - Codex agents default to `cao_only`.
- Enforce strict mode isolation per session/turn execution path: no mixed pipelines, no in-turn parser chaining, and no silent fallback from one parser family to the other.
- Refactor CAO runtime turn handling to use parser-mode-specific engines behind a shared interface, so both modes are structurally consistent.
- Add runtime shadow parsing support for Codex CAO sessions (status classification + answer extraction from `mode=full`) so Codex can run in `shadow_only` mode when needed.
- Always run shared runtime post-processing regardless of parsing mode to provide a stable contract and observability (canonicalize status/provenance and record raw backend values; do not sanitize/rewrite extracted answer text).
- Remove parser fallback behavior entirely; the selected mode is authoritative for each session/turn.
- **BREAKING**: revise CAO session manifest schema to persist parsing mode explicitly (hard-break; no legacy manifest compatibility/migration support).
- Emit parser provenance metadata in turn events (selected mode, source output mode, parser family, and parser preset/format metadata where applicable) for observability.
- Preserve AGENTSYS identity and tmux manifest-pointer contracts unchanged; parsing mode selection must not alter naming, pointer publication, or name-based resume/stop addressing semantics.

## Capabilities

### New Capabilities
- `cao-codex-output-extraction`: Runtime-owned shadow parsing for Codex CAO `mode=full` output, including status detection and last-answer extraction for `shadow_only` sessions.

### Modified Capabilities
- `brain-launch-runtime`: CAO prompt execution adds explicit `parsing_mode` selection (`cao_only` or `shadow_only`), strict per-session parser-family isolation, and deterministic mode-specific turn handling.
- `cao-claude-code-output-extraction`: Clarify that Claude shadow parsing requirements apply to `shadow_only` execution mode, and codify strict non-mixing with `cao_only` in a single turn.

## Impact

- Affected runtime backend:
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py`
- New/updated parser modules under:
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/`
- Session/launch metadata surfaces that carry parser-mode selection/provenance:
  - `src/agent_system_dissect/agents/brain_launch_runtime/cli.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/runtime.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/models.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/launch_plan.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/manifest.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/boundary_models.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/schemas/session_manifest*.json`
- Unit tests for CAO runtime mode behavior and Codex shadow parsing:
  - `tests/unit/agents/brain_launch_runtime/`
