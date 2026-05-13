## 1. Routing And Operation Surface

- [x] 1.1 Add `validate-loop` to the top-level execution operation list.
- [x] 1.2 Add routing for `subskills/execution/validate-loop.md`.
- [x] 1.3 Revise top-level execution-stage order guidance to `prepare-agents`, `prepare-workspace`, `validate-loop`, `start`.
- [x] 1.4 Update `agents/openai.yaml` if needed so execution readiness validation remains discoverable without making the prompt verbose.

## 2. Prepare Agents And Workspace Boundaries

- [x] 2.1 Revise `prepare-agents.md` so it no longer requires workspace readiness before running.
- [x] 2.2 Revise `prepare-agents.md` to produce concrete agent/profile facts needed by workspace setup.
- [x] 2.3 Revise `prepare-agents.md` to allow live launch to be deferred until workspace and `validate-loop` readiness exist.
- [x] 2.4 Revise `prepare-workspace.md` so it consumes prepared agent/profile facts from `prepare-agents`.
- [x] 2.5 Preserve the rule that `prepare-agents` and `prepare-workspace` do not call each other.

## 3. Validate Loop And Start

- [x] 3.1 Add `subskills/execution/validate-loop.md` with read-first references, preconditions, inputs, checks, output report, and constraints.
- [x] 3.2 Make `validate-loop` check prepared agents/profiles, generated and maintained skill bindings, workspace facts, launch cwd and memo posture, mailbox/gateway/notifier posture, harness availability, run artifact/state readiness, and no in-chat waiting posture.
- [x] 3.3 Revise `start.md` so it requires `validate-loop` or performs only a final lightweight readiness check before sending the first trigger.
- [x] 3.4 Ensure `validate-loop` is read-only in normal behavior and does not repair missing preparation.

## 4. Validation And Reference Guidance

- [x] 4.1 Revise `validate-execplan.md` so it checks generated stage order and generated package shape, not live runtime readiness.
- [x] 4.2 Revise generated defaults and platform-boundary reference pages to describe the corrected execution order and validation split.
- [x] 4.3 Update workspace-contract and agent-binding generation guidance if needed so concrete agent/profile facts are clear inputs to workspace preparation.
- [x] 4.4 Update relevant `dev/design/` pages to explain the corrected execution-stage rationale.

## 5. Verification

- [x] 5.1 Check Markdown links and relative references for all modified skill pages.
- [x] 5.2 Run `openspec status --change revise-v5-execution-prep-order --json` and confirm the change is apply-ready.
- [x] 5.3 Run `git diff --check`.
