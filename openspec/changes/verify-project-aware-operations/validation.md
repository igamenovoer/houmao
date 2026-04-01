# Verification Evidence

Date: 2026-04-01

## Automated Matrix

- `pixi run ruff check tests/unit/project/test_overlay.py tests/unit/srv_ctrl/test_cleanup_commands.py tests/integration/srv_ctrl/test_cli_shape_contract.py`
  - Result: passed
- `pixi run pytest tests/unit/project/test_overlay.py tests/unit/test_owned_paths.py tests/unit/srv_ctrl/test_project_commands.py tests/unit/srv_ctrl/test_mailbox_commands.py tests/unit/srv_ctrl/test_cleanup_commands.py tests/unit/srv_ctrl/test_commands.py tests/unit/server/test_config.py tests/unit/server/test_commands.py tests/unit/passive_server/test_config.py tests/unit/srv_ctrl/commands/test_runtime_artifacts_join.py tests/unit/demo/minimal_agent_launch/test_demo_contract.py tests/unit/demo/single_agent_mail_wakeup/test_demo_pack.py tests/integration/srv_ctrl/test_cli_shape_contract.py`
  - Result: `221 passed`

The broadened matrix covers:

- overlay-selection precedence and nearest-ancestor reuse
- `.git` file and directory worktree-boundary handling
- non-creating `houmao-mgr project status`
- implicit bootstrap and selected-root detail reporting
- overlay-local runtime or jobs or mailbox placement
- explicit runtime-root override behavior for cleanup
- project-context `houmao-mgr server start` without an explicit `--runtime-root`
- maintained demo contract surfaces for `minimal-agent-launch` and `single-agent-mail-wakeup`

## Representative Maintained Workflow Checks

- `bash -n scripts/demo/minimal-agent-launch/scripts/run_demo.sh`
  - Result: passed
- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --help`
  - Result: passed
- `scripts/demo/single-agent-mail-wakeup/run_demo.sh help`
  - Result: passed
- `scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier --help`
  - Result: passed

## Notes

This unattended validation pass used maintained operator subprocess integration tests plus maintained demo wrapper and contract coverage as the representative workflow evidence for the project-aware contract. Live provider-backed demo runs were intentionally not required for this close-out pass because they depend on external CLI session behavior beyond the maintained overlay-local root contract itself.
