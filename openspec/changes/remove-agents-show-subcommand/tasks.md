## 1. CLI Surface Removal

- [ ] 1.1 Remove `show_agent_command()` and the now-unused CLI import/wiring for that subcommand from `src/houmao/srv_ctrl/commands/agents/core.py`, while preserving `managed_agent_detail_payload()` and its helper chain for non-CLI callers.
- [ ] 1.2 Verify the `houmao-mgr agents` help surface no longer advertises `show` and that supported inspection guidance still points to `state`, `agents gateway tui ...`, and related remaining commands.

## 2. Spec, Docs, And Workflow Cleanup

- [ ] 2.1 Broaden the `houmao-srv-ctrl-native-cli` delta and add companion delta specs for `houmao-mgr-agents-join` and `houmao-mgr-registry-discovery` so the active spec corpus no longer requires `houmao-mgr agents show`.
- [ ] 2.2 Update reference docs that currently list or recommend `houmao-mgr agents show`, including native CLI and pair-workflow guidance.
- [ ] 2.3 Update workflow documents and examples that invoke `houmao-mgr agents show` so they use supported inspection commands instead.

## 3. Test And Verification Updates

- [ ] 3.1 Update CLI shape and command-contract tests that currently expect the `show` subcommand to exist, including a negative help assertion that `houmao-mgr agents --help` no longer lists `show`.
- [ ] 3.2 Update any workflow fixtures or demo-related assertions that reference the removed `houmao-mgr agents show` CLI surface so the test suite reflects the smaller command set without removing preserved non-CLI detail helpers.
- [ ] 3.3 Run a repository-wide grep sweep for `agents show` across `src/`, `tests/`, `docs/`, and `openspec/`, and confirm no active supported-surface references remain.
