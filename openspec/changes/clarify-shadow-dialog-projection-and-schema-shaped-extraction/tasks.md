## 1. Clarify the shadow projection contract

- [ ] 1.1 Update the shared shadow parser models, serializer-facing wording, and developer docs to define `normalized_text` as the closer-to-source surface and `dialog_text` as a best-effort heuristic projection rather than exact recovered text.
- [ ] 1.2 Update the Claude and Codex shadow parser modules, comments, and tests so projection behavior is described and validated as heuristic cleanup over known TUI patterns instead of exact text extraction.

## 2. Audit and harden downstream consumers

- [ ] 2.1 Keep `_TurnMonitor` projection-diff completion logic, but revise its documentation and tests so it is explicitly treated as coarse change detection rather than semantic answer extraction.
- [ ] 2.2 Harden runtime-owned machine parsing paths such as mailbox result extraction so their correctness is grounded in explicit schema/sentinel contracts over available text surfaces instead of assuming exact `dialog_projection.dialog_text` fidelity.
- [ ] 2.3 Update `shadow_answer_association` examples and nearby guidance to present caller-owned extraction as an explicit best-effort escape hatch, with schema-shaped prompting recommended for reliable downstream use.

## 3. Revise operator-facing surfaces

- [ ] 3.1 Update interactive demo inspect runtime, CLI help, models, and rendering so `--with-output-text` is described as a best-effort projected diagnostic tail rather than dependable clean-text extraction.
- [ ] 3.2 Update reference and maintainer docs for realm-controller shadow mode, troubleshooting, shared parser contracts, and interactive demo inspection to explain the revised reliability tiers and recommended schema-shaped extraction pattern.

## 4. Verify the revised contract

- [ ] 4.1 Update or add unit tests for shadow projection contract semantics, mailbox-result extraction behavior, and interactive demo inspect output wording.
- [ ] 4.2 Run the targeted validation set for shadow parser, mailbox command, and interactive demo inspect coverage and confirm the updated contract holds end-to-end.
