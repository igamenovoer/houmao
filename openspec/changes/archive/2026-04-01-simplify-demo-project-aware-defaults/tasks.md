## 1. Simplify the minimal launch demo

- [x] 1.1 Update `scripts/demo/minimal-agent-launch/scripts/run_demo.sh` so the runner uses one generated overlay root as the local Houmao-owned state anchor and removes redundant separate agent-definition and runtime root env overrides.
- [x] 1.2 Update `scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md` and any maintained demo-surface references so the documented generated output layout and example commands match the new overlay-local runtime and jobs placement.

## 2. Simplify the single-agent wake-up demo

- [x] 2.1 Update `src/houmao/demo/single_agent_mail_wakeup/runtime.py` and related layout helpers so the demo environment keeps the redirected overlay selector and isolated registry override but drops redundant agent-definition, runtime, and jobs overrides.
- [x] 2.2 Update `src/houmao/demo/single_agent_mail_wakeup/models.py`, reporting or expected-report fixtures, and `scripts/demo/single-agent-mail-wakeup/README.md` so the maintained output layout describes overlay-local runtime, jobs, and mailbox state under `outputs/overlay/`.

## 3. Verify the supported demo surface

- [x] 3.1 Update focused demo tests, including `tests/unit/demo/single_agent_mail_wakeup/test_demo_pack.py`, to assert the simplified environment and output layout.
- [x] 3.2 Add or refresh focused verification for the minimal launch demo so the supported runner or tutorial assertions cover the new single-overlay root contract.
- [x] 3.3 Run the focused demo test targets and `openspec status --change simplify-demo-project-aware-defaults` to confirm the follow-up change is implementation-ready.
