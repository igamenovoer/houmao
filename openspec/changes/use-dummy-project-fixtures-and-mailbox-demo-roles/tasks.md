## 1. Add Dummy-Project And Mailbox-Demo Fixtures

- [ ] 1.1 Create a tracked mailbox-ready dummy project under `tests/fixtures/dummy-projects/` and helper logic to provision it as an isolated git-backed demo workdir.
- [ ] 1.2 Add lightweight mailbox-demo roles, Claude/Codex brain recipes, and dedicated mailbox-demo blueprints under `tests/fixtures/agents/`.
- [ ] 1.3 Update fixture guidance to explain when to use dummy-project/lightweight-role fixtures versus repo-worktree/heavyweight-role fixtures.

## 2. Switch The Tutorial Pack To Dummy-Project Workdirs And Add Inspection

- [ ] 2.1 Replace mailbox tutorial-pack repo-worktree provisioning with copied dummy-project provisioning under the demo-owned output/home tree and update the default demo parameters accordingly.
- [ ] 2.2 Add `run_demo.sh inspect --agent <sender|receiver>` with tmux attach, terminal-log, live tool-state, and optional output-tail diagnostics for the selected tutorial session.
- [ ] 2.3 Update the tutorial-pack README, report contract, and expected verification artifacts to document the dummy-project defaults and the inspect/watch workflow.

## 3. Reclassify Deterministic And Real-Agent Coverage

- [ ] 3.1 Update the tracked integration lane to use the new dummy-project/lightweight-role fixtures while continuing to exercise the direct runtime mail path without synthetic mailbox-result fallback.
- [ ] 3.2 Add an opt-in real-agent smoke entrypoint that uses actual local Claude/Codex CLIs with clear prerequisite failures and points maintainers at the new inspect surface while turns are running.
- [ ] 3.3 Revise the related docs and regression expectations so deterministic automatic coverage and opt-in real-agent smoke are described as separate promises.
