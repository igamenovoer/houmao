## 1. CLI Surface Removal

- [x] 1.1 Remove `show_agent_command()` and the now-unused CLI import/wiring for that subcommand from `src/houmao/srv_ctrl/commands/agents/core.py`, while preserving `managed_agent_detail_payload()` and its helper chain for non-CLI callers.
- [x] 1.2 Verify the `houmao-mgr agents` help surface no longer advertises `show` and that supported inspection guidance still points to `state`, `agents gateway tui ...`, and related remaining commands.
- [x] 1.3 Migrate CLI consumers in `src/houmao/demo/gateway_mail_wakeup_demo_pack/` away from `houmao-mgr agents show` while preserving the demo's identity/bootstrap flow.

## 2. Spec, Docs, And Workflow Cleanup

- [x] 2.1 Broaden the `houmao-srv-ctrl-native-cli` delta and add companion delta specs for `houmao-mgr-agents-join`, `houmao-mgr-registry-discovery`, and `docs-cli-reference` so the active spec corpus no longer requires `houmao-mgr agents show`.
- [x] 2.2 Update reference docs that currently list or recommend `houmao-mgr agents show`, including native CLI and pair-workflow guidance.
- [x] 2.3 Update workflow documents and examples that invoke `houmao-mgr agents show` so they use supported inspection commands instead.

## 3. Test And Verification Updates

- [x] 3.1 Update CLI shape and command-contract tests that currently expect the `show` subcommand to exist, including a negative help assertion that `houmao-mgr agents --help` no longer lists `show`.
- [x] 3.2 Update workflow fixtures, demo tests, and related assertions that reference the removed `houmao-mgr agents show` CLI surface so the test suite reflects the smaller command set without removing preserved non-CLI detail helpers.
- [x] 3.3 Run a repository-wide grep sweep for `agents show` across `src/`, `tests/`, `docs/`, and `openspec/`, and confirm no active supported-surface references remain.
