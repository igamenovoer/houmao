## Dependency Order

- Foundation first: complete `1.x` before `2.x`.
- Provider contract changes before runtime wiring: complete `1.x` and `2.x` before `3.x`.
- Runtime/result changes before test rewrites: complete `3.x` before `4.x`.

## 1. Parser Contract Refactor

- [ ] 1.1 Add frozen shared/base shadow-parser core models for `SurfaceAssessment` and `DialogProjection`, including parser metadata/anomaly carriage and typed projection provenance.
- [ ] 1.2 Add provider-specific subclasses for Claude and Codex state/projection artifacts, including provider-specific `ui_context` vocabularies and evidence fields.
- [ ] 1.3 Refactor the shared shadow-parser stack interface so core parser operations return state/projection artifacts instead of prompt-associated answer extraction.
- [ ] 1.4 Remove or deprecate shared parser APIs whose contract depends on prompt-associated answer extraction or baseline-owned answer association.

## 2. Provider Parser Updates

- [ ] 2.1 Refactor the Claude shadow parser to produce `ClaudeSurfaceAssessment` and `ClaudeDialogProjection` from `mode=full` snapshots according to `contracts/claude-state-contracts.md`.
- [ ] 2.2 Refactor the Codex shadow parser to produce `CodexSurfaceAssessment` and `CodexDialogProjection` from `mode=full` snapshots according to `contracts/codex-state-contracts.md`, including alignment with the shared `slash_command` `ui_context`.
- [ ] 2.3 Add provider-specific projection/state rules and fixtures so prompt chrome, spinner/footer noise, menu UI, slash-command UI, and provider-specific contexts are classified/projected correctly while essential visible dialog content is preserved.

## 3. Runtime Turn Monitoring And Result Surface

- [ ] 3.1 Define and implement a runtime-owned `TurnMonitor` that evolves or absorbs `_ShadowLifecycleTracker`, preserves unknown→stalled policy, and follows `contracts/turn-monitor-contracts.md`.
- [ ] 3.2 Update CAO `shadow_only` result/event payloads to remove shadow-mode `output_text` and instead expose first-class `dialog_projection`, `surface_assessment`, projection slices, and state/provenance metadata.
- [ ] 3.3 Gate runtime success terminality on `ready_for_input` plus (`evt_projection_changed` or observed post-submit `working`), while treating `waiting_user_answer`, `unsupported`, `disconnected`, and terminal `stalled` as non-success exits.
- [ ] 3.4 Add an optional associator protocol/helper and ship `TailRegexExtractAssociator(n, pattern)` with unit tests as the concrete caller-side extraction example.

## 4. Docs And Tests

- [ ] 4.1 Update OpenSpec delta specs, reference docs, and troubleshooting docs to describe the new separation between parser state/projection and caller-owned answer association, including `contracts/claude-state-contracts.md`, `contracts/codex-state-contracts.md`, and `contracts/turn-monitor-contracts.md`.
- [ ] 4.2 Rewrite parser/runtime unit tests in `tests/unit/agents/brain_launch_runtime/test_claude_code_shadow_parser.py`, `tests/unit/agents/brain_launch_runtime/test_codex_shadow_parser.py`, and `tests/unit/agents/brain_launch_runtime/test_cao_client_and_profile.py`, plus fixtures under `tests/fixtures/shadow_parser/`, so they validate projection/state semantics and no-association guarantees instead of parser-owned final-answer extraction.
- [ ] 4.3 Add integration coverage for CAO `shadow_only` turns that validates projected dialog payloads, head/tail slices, runtime terminality gating, and the absence of an implicit authoritative parser-owned answer contract.
