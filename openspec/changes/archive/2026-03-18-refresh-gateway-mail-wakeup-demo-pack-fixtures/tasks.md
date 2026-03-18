## 1. Refresh Default Fixture Shape

- [x] 1.1 Update `scripts/demo/gateway-mail-wakeup-demo-pack/inputs/demo_parameters.json` and related helper parsing so the tracked default agent uses the lightweight `mailbox-demo` blueprint family and records the selected dummy-project fixture.
- [x] 1.2 Replace the gateway wake-up pack's repository-worktree provisioning with copied dummy-project provisioning in `scripts/demo/gateway-mail-wakeup-demo-pack/scripts/tutorial_pack_helpers.py`, including fresh git initialization and explicit managed-project metadata.
- [x] 1.3 Update rerun and stale-directory handling so existing pack-managed dummy-project repos can be reprovisioned safely while old repo-worktree or unmanaged `project/` directories fail with clear guidance.

## 2. Update Demo Contract And Documentation

- [x] 2.1 Refresh the demo's start and automatic workflow outputs, persisted state, and expected-report snapshot so they reflect the copied dummy-project and lightweight mailbox-demo defaults instead of repository-worktree and heavyweight-role assumptions.
- [x] 2.2 Revise `scripts/demo/gateway-mail-wakeup-demo-pack/README.md` to teach the new default fixture shape, explain why the pack is intentionally narrower than repo-scale engineering demos, and document how maintainers should handle stale old demo roots.
- [x] 2.3 Update any gateway reference docs that describe this pack as the runnable wake-up walkthrough if they currently imply repository-worktree or heavyweight-role defaults.

## 3. Strengthen Regression Coverage

- [x] 3.1 Expand `tests/unit/demo/test_gateway_mail_wakeup_demo_pack.py` so it fails when tracked parameters or report expectations regress back to heavyweight blueprint or repository-worktree assumptions.
- [x] 3.2 Add deterministic helper-level coverage for the refreshed provisioning and orchestration path, including copied dummy-project setup and explicit failure on stale non-managed project directories.
- [x] 3.3 Run the targeted demo-pack tests and relevant OpenSpec validation so the refreshed change is ready for implementation and later archive.
