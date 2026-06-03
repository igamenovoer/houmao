## Implementation Summary

### Changes

| Area | Summary |
|---|---|
| Root CLI fallback | `_render_uncaught_exception()` now reports unexpected internal errors with exception-class evidence instead of using a bare class name for empty exceptions. |
| Managed-agent local authority | Added `_require_live_local_controller(...)` and stale/degraded diagnostic formatting with operation name, target evidence, and maintained recovery commands. |
| Public command helpers | Applied the live-controller guard across managed-agent state/detail, prompt, interrupt, gateway, mail, turn, late mailbox, and memory paths that require live local runtime authority. |
| Regression coverage | Added CLI-level and helper-level tests for stale/degraded target diagnostics and root fallback behavior. |

### Scan Classification

Detailed scan notes are recorded in `scan-notes.md`.

### Verification

| Command | Result |
|---|---|
| `pixi run pytest tests/unit/srv_ctrl/test_commands.py tests/unit/srv_ctrl/test_managed_agents.py -k "stale_target_diagnostic or unavailable or AssertionError or empty_uncaught_assertion or gateway_status_rejects or gateway_tui_state_rejects or managed_agent_state_rejects or mail_status_rejects or stop_managed_agent_recovers_stale or stop_managed_agent_recovers_degraded or relaunch_degraded_or_stale"` | Passed, `9 passed, 136 deselected`. |
| `pixi run pytest tests/unit/srv_ctrl/test_commands.py tests/unit/srv_ctrl/test_managed_agents.py tests/unit/srv_ctrl/commands/test_agents_workspace.py` | Passed, `146 passed`. |
| `pixi run lint` | Passed, `All checks passed!`. |
| `pixi run typecheck` | Passed, `Success: no issues found in 333 source files`. |
| `pixi run test` | Passed, `1947 passed, 13 skipped in 153.91s`. |
