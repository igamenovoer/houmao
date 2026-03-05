## Context

The CAO runtime backend currently has asymmetric parsing paths in `CaoRestSession`:
- Claude turns use a runtime-owned shadow parser over `output?mode=full`.
- Non-Claude turns (including Codex) use CAO-native status/output semantics (`GET /terminals/{id}` + `output?mode=last`, with current fallback behavior when `mode=last` is unavailable).

This asymmetry works operationally, but it couples behavior to tool-specific branches and leaves fallback policy implicit. The new requirement is to keep parser families decoupled and selectable as whole modes, with no mixed per-turn fallback chain.

Constraints:
- We do not modify upstream CAO implementation.
- We keep CAO REST as the backend boundary.
- We preserve existing non-CAO backends (`codex_app_server`, headless backends).

## Goals / Non-Goals

**Goals:**
- Define exactly two CAO parsing modes: `cao_only` and `shadow_only`.
- Make parsing mode a configuration-resolved value with explicit per-tool defaults (`claude -> shadow_only`, `codex -> cao_only`).
- Enforce strict per-session/per-turn parser-family isolation (no mixed parser pipeline).
- Refactor CAO turn execution behind a mode-specific engine interface.
- Add Codex runtime shadow parsing so Codex can run in `shadow_only` mode.
- Ensure shared runtime post-processing (stable status/provenance contract + observability) runs before surfacing turn results.
- Remove parser fallback behavior entirely: no in-turn fallback and no cross-mode fallback workflow.
- Revise session manifest schema to persist parsing mode and require adoption of the new schema version.
- Provide clear parser provenance metadata for observability and debugging.
- Preserve AGENTSYS identity/tmux manifest-pointer behavior exactly as currently implemented.

**Non-Goals:**
- Modifying vendored/upstream CAO parser logic.
- Adding a hybrid mode (`cao_then_shadow`, `shadow_then_cao`) or in-turn fallback chaining.
- Introducing mode-switch fallback workflows between turns/sessions.
- Changing behavior of non-CAO backends.
- Providing compatibility support for legacy CAO manifests that do not carry parsing mode.

## Decisions

### 1) Introduce explicit `parsing_mode` for CAO sessions

**Decision:** CAO-backed sessions carry a resolved `parsing_mode` with only:
- `cao_only`
- `shadow_only`

Mode is resolved at session start from configuration (caller-provided value and/or tool default), and persisted in session state/manifest metadata for resume consistency.

Default mapping:
- `tool=claude` -> `shadow_only`
- `tool=codex` -> `cao_only`

Supported `(tool, parsing_mode)` pairs:
- `(claude, shadow_only)` (default)
- `(claude, cao_only)`
- `(codex, cao_only)` (default)
- `(codex, shadow_only)`

**Rationale:** Makes parser policy explicit and auditable, and prevents hidden behavior drift.

**Alternatives considered:**
- Implicit tool-based mode selection only: rejected because it preserves asymmetry and makes fallback policy opaque.
- Per-turn mode override: rejected because it complicates reasoning and encourages accidental mixing.

### 2) Use two separate turn engines with a shared interface

**Decision:** `CaoRestSession` delegates turn handling to one engine selected by `parsing_mode`:
- `CaoOnlyTurnEngine`
- `ShadowOnlyTurnEngine`

Shared engine contract includes readiness wait, submit, completion wait, answer extraction, and diagnostics snapshot.

**Rationale:** Structural consistency without coupling parser internals.

**Alternatives considered:**
- Keep tool-specific branching in one method: rejected due to increasing complexity and regression risk.

### 3) Enforce strict non-mixing within a turn

**Decision:** A turn executed in one mode MUST NOT call extraction/gating methods from the other parser family.
- `cao_only` uses CAO status + CAO `mode=last` answer path.
- `shadow_only` uses runtime parser + `mode=full` only.

Any parser failure returns a mode-specific error; no chained fallback in the same turn and no operational fallback that retries under the other mode.

**Rationale:** Satisfies decoupling requirement and simplifies testability.

**Alternatives considered:**
- Soft fallback from one mode to the other inside the same turn: rejected explicitly by requirement.

### 4) Add Codex shadow parser module aligned to existing Claude shadow parser shape

**Decision:** Implement a runtime Codex shadow parser for `shadow_only` Codex sessions, following the same lifecycle primitives already used by Claude shadow parsing:
- baseline capture
- shadow status classification (including waiting-user-answer detection)
- answer extraction
- explicit waiting-user-answer error surfacing

**Rationale:** Enables consistent mode semantics across tools while keeping parser implementations tool-specific.

**Alternatives considered:**
- Reusing CAO Codex parser behavior in `shadow_only`: rejected because it violates parser-family decoupling.

### 5) Keep shared output post-processing outside parser engines

**Decision:** Apply a shared, parser-agnostic post-processing step to each turn result in both modes to provide a stable runtime contract and observability.

This shared post-processing step is not shadow parsing and does not attempt to sanitize/rewrite extracted answer text. Instead, it:
- canonicalizes backend-specific status/provenance into runtime-stable values for downstream consumers, and
- records/logs raw backend status/provenance for debugging.

In `cao_only`, extracted answer text is treated as a passthrough from CAO `output?mode=last` (no runtime shadow parsing and no in-turn fallback).

**Rationale:** Stable downstream contract and observability without parser mixing.

**Alternatives considered:**
- Mode-specific output formatting only: rejected because callers expect normalized output regardless of mode.

### 6) Keep AGENTSYS identity/tmux manifest-pointer contracts unchanged

**Decision:** Parsing-mode refactor SHALL NOT change recently introduced AGENTSYS contracts:
- canonical tmux session naming (`AGENTSYS-...`),
- tmux env pointer publication (`AGENTSYS_MANIFEST_PATH`),
- name-based manifest resolution via tmux session + env pointer,
- manifest/session mismatch fail-fast checks used by prompt/stop flows.

These contracts must hold for both `cao_only` and `shadow_only`.

**Rationale:** Parsing mode controls turn parsing semantics only. Agent identity and session addressing are independent contracts and must remain stable.

**Alternatives considered:**
- Reworking identity/addressing while refactoring parsing mode: rejected to minimize scope and reduce regression risk.

## Risks / Trade-offs

- [Codex shadow parser drift as Codex UI evolves] -> Mitigation: versioned parser presets/tests and fixture-based parser regression coverage.
- [No fallback can increase immediate failures for a mismatched mode choice] -> Mitigation: clear mode-specific diagnostics and explicit configuration defaults by tool.
- [Mode/tool selection confusion] -> Mitigation: fail-fast validation on unknown parsing modes and explicit documentation of supported pairs and tool defaults.
- [Breaking manifest schema can disrupt existing sessions] -> Mitigation: accepted (hard-break); fail fast on schema mismatch and fix forward.
- [Refactor complexity in CAO backend] -> Mitigation: incremental extraction (preserve current behavior first, then mode-wire and extend).
- [Parser refactor may accidentally regress AGENTSYS identity/addressing] -> Mitigation: explicit invariants + dedicated non-regression tests across both parsing modes.

## Migration Plan

1. Add `parsing_mode` to CAO launch/session state surfaces (launch metadata + manifest boundary models), and bump session manifest schema for CAO payload changes.
2. Implement parsing-mode resolution from configuration, including defaults (`claude -> shadow_only`, `codex -> cao_only`).
3. Extract existing generic CAO path into `CaoOnlyTurnEngine` without behavior change.
4. Extract existing Claude shadow path into `ShadowOnlyTurnEngine` without behavior change.
5. Route `CaoRestSession.send_prompt()` through mode-selected engine.
6. Add Codex shadow parser and wire Codex `shadow_only` engine behavior.
7. Add parser provenance fields in turn event payloads (mode, parser family, output source mode, and parser preset/format metadata where applicable).
8. Update tests:
   - mode selection and strict non-mixing behavior,
   - mode-specific readiness/completion/extraction,
   - Codex shadow parser fixtures.
9. Add AGENTSYS non-regression tests proving naming/pointer/resolution contracts are unchanged for both parsing modes.

No legacy compatibility strategy is provided for old CAO manifests without parsing mode (hard-break; no backward compatibility guarantees).

## Open Questions

- None currently.
