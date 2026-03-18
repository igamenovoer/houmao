## 1. Add Dummy-Project And Mailbox-Demo Fixtures

- [ ] 1.1 Create a tracked mailbox-ready dummy project under `tests/fixtures/dummy-projects/` with a concrete tiny starter manifest, and add helper logic that copies the source-only fixture then initializes a fresh pinned-metadata git repository as the isolated demo workdir.
- [ ] 1.2 Add the lightweight `mailbox-demo` role, `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml` brain recipes, and `mailbox-demo-claude.yaml` / `mailbox-demo-codex.yaml` blueprints under `tests/fixtures/agents/`.
- [ ] 1.3 Update fixture guidance to explain when to use dummy-project/lightweight-role fixtures versus repo-worktree/heavyweight-role fixtures, including a short selection rubric or decision tree.

## 2. Switch The Tutorial Pack To Dummy-Project Workdirs And Add Inspection

- [ ] 2.1 Replace mailbox tutorial-pack repo-worktree provisioning with copied dummy-project provisioning under the demo-owned output/home tree, initialize a fresh git repo after copy, and update `scripts/demo/mailbox-roundtrip-tutorial-pack/inputs/demo_parameters.json` to the mailbox-demo defaults.
- [ ] 2.2 Add `run_demo.sh inspect --agent <sender|receiver>` with tmux attach, terminal-log, live tool-state, and optional output-tail diagnostics for the selected tutorial session, implementing the full surface in one task with persisted metadata first and live/output-tail lookups layered on afterward.
- [ ] 2.3 Update the tutorial-pack README, report contract, and expected verification artifacts to document the dummy-project defaults and the inspect/watch workflow; refresh the expected snapshot and adjust sanitization only if new unstable fields require it.

## 3. Reclassify Deterministic And Real-Agent Coverage

- [ ] 3.1 Update the tracked integration lane and `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/run_automation_scenarios.py` to use the new dummy-project/lightweight-role fixtures while continuing to exercise the direct runtime mail path without synthetic mailbox-result fallback.
- [ ] 3.2 Add an opt-in real-agent smoke manual script under `tests/manual/` that uses actual local Claude/Codex CLIs with clear prerequisite failures and points maintainers at the new inspect surface while turns are running.
- [ ] 3.3 Revise the related docs and regression expectations so deterministic automatic coverage and opt-in real-agent smoke are described as separate promises.
