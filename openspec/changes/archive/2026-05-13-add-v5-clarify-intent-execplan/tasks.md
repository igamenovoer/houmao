## 1. Shared Clarification Protocol

- [x] 1.1 Add `subskills/reference/clarification-protocol.md` with the structured coverage-scan, prioritization, question, integration, validation, and summary rules.
- [x] 1.2 Ensure the protocol requires at most five accepted questions and exactly one question at a time.
- [x] 1.3 Ensure the protocol requires recommendation/suggestion text and immediate artifact updates after accepted answers.
- [x] 1.4 Ensure the protocol requires the mail runtime model as mandatory context for mail-driven loop behavior.

## 2. Intent Clarification

- [x] 2.1 Rename the canonical operation in `SKILL.md` from `clarify intent` to `clarify-intent`, preserving an unambiguous natural-language alias if useful.
- [x] 2.2 Rewrite `subskills/authoring/clarify-intent.md` to read the clarification protocol, runtime mail model, intention source, project context, and existing intent ADRs before asking.
- [x] 2.3 Add intent coverage categories for objective, completion, participants, topology, mail families, event/tick behavior, state, operator control, workspace/artifacts/evidence, project context, terminology, and omissions.
- [x] 2.4 Update `clarify-intent` actions so accepted answers are recorded in intent ADRs and reflected in `intention/` Markdown without editing generated `execplan/`.

## 3. Execplan Clarification

- [x] 3.1 Add `subskills/authoring/clarify-execplan.md`.
- [x] 3.2 Add `clarify-execplan` to `SKILL.md` operations and routing.
- [x] 3.3 Make `clarify-execplan` read generated execplan artifacts, prior execplan ADRs, the generation pipeline, generated contract defaults, platform boundaries, runtime mail model, and clarification protocol.
- [x] 3.4 Add execplan coverage categories for process, mail schemas/renderers/replies, state, harness, generated skills, agent bindings, run artifacts, validation, docs, manifest, platform boundaries, and no in-chat waiting.
- [x] 3.5 Make accepted execplan answers create or update `execplan/adrs/` and the affected generated execplan artifacts or downstream-stale notes.
- [x] 3.6 Ensure `clarify-execplan` reports intention-source gaps instead of silently inventing user intent in generated artifacts.

## 4. Documentation And Verification

- [x] 4.1 Update v5 developer design docs to describe the two clarification scopes and source-authority boundary.
- [x] 4.2 Update operation references in related authoring pages if they mention `clarify intent`.
- [x] 4.3 Validate Markdown links from `SKILL.md`, clarification pages, and reference pages.
- [x] 4.4 Run `git diff --check`.
- [x] 4.5 Verify the OpenSpec change is apply-ready.
