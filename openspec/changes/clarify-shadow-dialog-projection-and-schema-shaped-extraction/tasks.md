## 1. Refactor projection into modular processors

- [ ] 1.1 Introduce a shared projector abstraction and provider/version-aware processor-selection path in the shadow parser core/stack while preserving the existing `DialogProjection` result contract.
- [ ] 1.2 Refactor Claude projection logic into one or more swappable processor implementations selected independently from the monolithic parser method body.
- [ ] 1.3 Refactor Codex projection logic into one or more swappable processor implementations selected independently from the monolithic parser method body.
- [ ] 1.4 Add controlled processor override/injection support for tests and advanced callers, and ensure `projection_metadata.projector_id` reflects the selected processor instance.

## 2. Clarify the projection contract

- [ ] 2.1 Update the shared shadow parser models, serializer-facing wording, and developer docs to define `normalized_text` as the closer-to-source surface and `dialog_text` as a best-effort heuristic projection rather than exact recovered text.
- [ ] 2.2 Update the Claude and Codex shadow parser modules, comments, and tests so projection behavior is described and validated as heuristic cleanup over known TUI patterns instead of exact text extraction.
- [ ] 2.3 Keep `_TurnMonitor` projection-diff completion logic, but revise its documentation and tests so it is explicitly treated as coarse change detection rather than semantic answer extraction.

## 3. Audit and harden downstream consumers

- [ ] 3.1 Harden runtime-owned machine parsing paths such as mailbox result extraction so their correctness is grounded in explicit schema/sentinel contracts over available text surfaces instead of assuming exact `dialog_projection.dialog_text` fidelity.
- [ ] 3.2 Update `shadow_answer_association` examples and nearby guidance to present caller-owned extraction as an explicit best-effort escape hatch, with schema-shaped prompting recommended for reliable downstream use.

## 4. Revise operator-facing surfaces

- [ ] 4.1 Update interactive demo inspect runtime, CLI help, models, and rendering so `--with-output-text` is described as a best-effort projected diagnostic tail rather than dependable clean-text extraction.
- [ ] 4.2 Update reference and maintainer docs for realm-controller shadow mode, troubleshooting, shared parser contracts, parser architecture, and interactive demo inspection to explain the revised reliability tiers and modular projector pattern.

## 5. Verify the revised contract and refactor

- [ ] 5.1 Update or add unit tests for projector selection/swapping, shadow projection contract semantics, mailbox-result extraction behavior, and interactive demo inspect output wording.
- [ ] 5.2 Run the targeted validation set for shadow parser, mailbox command, and interactive demo inspect coverage and confirm the modular projector refactor holds end-to-end.
