## 1. Scan and Classify Current Error Surfaces

- [x] 1.1 Reproduce the reported stale managed-agent path in a focused unit fixture for `houmao-mgr agents single --agent-name <name> gateway status`.
- [x] 1.2 Scan maintained public `houmao-mgr` command code for `except Exception`, `str(exc) or exc.__class__.__name__`, `raise click.ClickException(str(exc))`, and assertion-backed access to `ManagedAgentTarget.client`, `ManagedAgentTarget.controller`, or `ManagedAgentTarget.record`.
- [x] 1.3 Classify scan results as public operator-facing issues, already-actionable domain conversions, internal-only code, test-only code, or out-of-scope larger refactors.

## 2. Shared Diagnostics

- [x] 2.1 Add a shared managed-agent target diagnostic helper that formats stale and degraded local target failures with operation name, agent name/id, lifecycle state, tmux session, manifest/session-root evidence, and recovery command hints.
- [x] 2.2 Add a shared live-controller guard for local managed-agent operations that require `target.controller`, while preserving server/external branches and existing stop/relaunch stale recovery behavior.
- [x] 2.3 Update the root `houmao-mgr` uncaught-exception fallback so empty implementation exceptions render as unexpected internal errors with exception-class evidence instead of bare class names.

## 3. Command Updates

- [x] 3.1 Apply the live-controller guard to gateway lifecycle/status, gateway TUI, gateway reminder, gateway mail-notifier, gateway prompt, gateway interrupt, and gateway send-keys helper paths that currently dereference `target.controller`.
- [x] 3.2 Apply the live-controller guard to managed-agent state/detail, prompt, interrupt, mail, workspace, turn, or other scanned public command helper paths that require a live local controller.
- [x] 3.3 Improve public command-boundary `click.ClickException(str(exc))` conversions found by the scan when local context can provide a clearer cause or recovery hint.
- [x] 3.4 Document any scanned implementation-level patterns intentionally left unchanged because they are test-only, demo-only, non-public, or require a separate design change.

## 4. Regression Tests

- [x] 4.1 Add tests proving stale and degraded managed-agent targets produce actionable errors for gateway status/TUI paths without surfacing `Error: AssertionError`.
- [x] 4.2 Add tests proving state/detail and one representative mail or workspace command reject stale/degraded targets before controller access.
- [x] 4.3 Add tests proving stop/relaunch still use their lifecycle recovery behavior for stale/degraded active local records.
- [x] 4.4 Add tests proving the root fallback renders empty `AssertionError` and non-empty unexpected exceptions as internal-error diagnostics without tracebacks.
- [x] 4.5 Preserve existing selector-miss and pair-authority failure wording tests.

## 5. Verification

- [x] 5.1 Run focused unit tests for `tests/unit/srv_ctrl/test_commands.py`, `tests/unit/srv_ctrl/test_managed_agents.py`, and any command-family tests touched by the scan.
- [x] 5.2 Run `pixi run lint` and `pixi run typecheck`.
- [x] 5.3 Run `pixi run test`.
- [x] 5.4 Record verification results and scan classification notes in the implementation summary.
