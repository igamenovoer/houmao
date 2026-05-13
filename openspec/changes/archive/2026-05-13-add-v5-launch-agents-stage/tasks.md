## 1. Operation Surface And Routing

- [x] 1.1 Add `launch-agents` to the top-level v5 execution operation list.
- [x] 1.2 Add routing for `subskills/execution/launch-agents.md`.
- [x] 1.3 Revise top-level execution-stage order guidance to `prepare-agents`, `prepare-workspace` or equivalent manual workspace evidence when required, `validate-loop`, `launch-agents`, `start`.
- [x] 1.4 Update `agents/openai.yaml` if needed so launch readiness remains discoverable without making the prompt verbose.

## 2. Execution Stage Boundaries

- [x] 2.1 Add `subskills/execution/launch-agents.md` with read-first references, preconditions, inputs, actions, report, and constraints.
- [x] 2.2 Make `launch-agents` launch only prepared participants through maintained Houmao launch surfaces and report live-agent/session facts.
- [x] 2.3 Ensure `launch-agents` does not create profiles, install skills, prepare workspaces, repair mailbox/gateway posture, mutate harness state, send loop-start work, or deliver the first trigger.
- [x] 2.4 Revise `prepare-agents.md` so live launch is not normal preparation behavior and prepared launch facts are explicit outputs.
- [x] 2.5 Revise `validate-loop.md` so it checks pre-launch readiness and launchability, not required live-agent state.
- [x] 2.6 Revise `validate-loop.md` to accept either `prepare-workspace` output or explicit equivalent manual workspace readiness evidence when workspace posture is required.
- [x] 2.7 Revise `start.md` so it requires a current `launch-agents` report or equivalent live-agent/session facts and does not launch agents.

## 3. Generated Guidance And Validation

- [x] 3.1 Revise `validate-execplan.md` so generated lifecycle guidance must separate `launch-agents` from `start`.
- [x] 3.2 Revise `validate-execplan.md` so generated lifecycle guidance accepts manual workspace readiness evidence as an alternative to the `prepare-workspace` command when documented.
- [x] 3.3 Revise generated defaults and platform-boundary reference pages to describe launch as a separate runtime transition.
- [x] 3.4 Update workspace-contract and agent-binding generation guidance if needed so prepared launch facts and manual workspace evidence are clear inputs to validation and launch.
- [x] 3.5 Update relevant `dev/design/` pages to explain the corrected execution-stage rationale.

## 4. Consistency And Verification

- [x] 4.1 Search the v5 skill package for stale wording that implies `prepare-agents` launches by default or `start` launches agents.
- [x] 4.2 Check Markdown links and relative references for modified and added skill pages.
- [x] 4.3 Run `openspec status --change add-v5-launch-agents-stage --json` and confirm the change is apply-ready.
- [x] 4.4 Run `git diff --check`.
