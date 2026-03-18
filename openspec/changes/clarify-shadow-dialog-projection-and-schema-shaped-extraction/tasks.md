## 1. Refactor projection into modular processors

- [ ] 1.1 Introduce a shared projector abstraction as a Protocol-style contract over already-normalized snapshots, plus provider parser-owned version-aware processor-selection path in the shadow parser core/stack while preserving the existing `DialogProjection` result contract and shared assembly responsibilities.
- [ ] 1.2 Refactor Claude projection logic into one or more swappable processor implementations selected independently from the monolithic parser method body.
- [ ] 1.3 Refactor Codex projection logic into one or more swappable processor implementations selected independently from the monolithic parser method body.
- [ ] 1.4 Add controlled processor override/injection support at both provider parser construction and `ShadowParserStack` construction, with stack-level override acting as pass-through, and ensure `projection_metadata.projector_id` reflects the selected processor instance.

## 2. Clarify the projection contract

- [ ] 2.1 Update the shared shadow parser models, serializer-facing wording, specs, and developer docs to define `normalized_text` as the closer-to-source surface, `dialog_text` as a best-effort heuristic projection rather than exact recovered text, and lifecycle/operator-diagnostic/machine-critical reliability tiers as an explicit part of the contract.
- [ ] 2.2 Update the Claude and Codex shadow parser modules, comments, and tests so projection behavior is described and validated as heuristic cleanup over known TUI patterns instead of exact text extraction.
- [ ] 2.3 Keep `_TurnMonitor` projection-diff completion logic, but revise its documentation and tests so it is explicitly treated as coarse change detection rather than semantic answer extraction.

## 3. Audit and harden downstream consumers

- [ ] 3.1 Harden runtime-owned machine parsing paths such as mailbox result extraction so their correctness is grounded in explicit schema/sentinel contracts over available text surfaces instead of assuming exact `dialog_projection.dialog_text` fidelity, while keeping protocol-specific extraction local until a second runtime-owned consumer justifies a shared helper.
- [ ] 3.2 Update `shadow_answer_association` examples and nearby guidance to present caller-owned extraction as an explicit best-effort escape hatch, with schema-shaped prompting recommended for reliable downstream use.

## 4. Make repo-owned CAO workflows shadow-first by default

- [ ] 4.1 Update runtime CLI/help/reference wording so CAO-backed Claude/Codex flows present `shadow_only` as the normal posture and `cao_only` as an explicit advanced/debug override.
- [ ] 4.2 Update the interactive full-pipeline demo turn artifacts, report verification, and tests so successful shadow-mode turns no longer rely on `done.message` as authoritative reply text or on mandatory non-empty `response_text`.
- [ ] 4.3 Update repo-owned CAO demo packs and verifiers that currently scrape `done.message`, including the shared `extract_response_text()` helpers in `cao-claude-session`, `cao-codex-session`, and `cao-claude-tmp-write`, so they use shadow-aware success evidence, schema/sentinel contracts, side-effect checks, or clearly labeled best-effort extraction instead.
- [ ] 4.4 Route any remaining repo-owned shadow-aware helper code that still bypasses `ShadowParserStack` through the shared stack-level abstraction instead of concrete provider parser classes where the parser stack now owns swappable projector selection.
- [ ] 4.5 Flip helper/test defaults to `shadow_only` where parsing mode is incidental, while keeping explicit `cao_only` coverage only in tests and workflows that intentionally exercise the CAO-native path.

## 5. Revise operator-facing surfaces

- [ ] 5.1 Update interactive demo inspect runtime, CLI help, models, and rendering so `--with-output-text` is described as a best-effort projected diagnostic tail rather than dependable clean-text extraction, while keeping the field name `output_text_tail`.
- [ ] 5.2 Update reference and maintainer docs for realm-controller shadow mode, troubleshooting, shared parser contracts, parser architecture, interactive demo inspection, and repo-owned CAO demo packs to explain the revised reliability tiers, shadow-first workflow posture, and modular projector pattern.

## 6. Verify the revised contract and refactor

- [ ] 6.1 Update or add unit tests for projector selection/swapping, stack/parser override pass-through behavior, shadow projection contract semantics including reliability tiers, shadow-first workflow defaults, mailbox-result extraction behavior, and interactive demo inspect/report wording.
- [ ] 6.2 Run the targeted validation set for shadow parser, mailbox command, interactive demo inspect/full-pipeline coverage, and affected demo-pack verification paths to confirm the modular projector refactor and shadow-first contract hold end-to-end.
