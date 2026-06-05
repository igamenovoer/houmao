## Why

`houmao-mgr` can currently surface implementation-level failures such as `Error: AssertionError`, which leaves operators unable to identify the failed resource, cause, or recovery path. This is especially visible when a command resolves a stale managed-agent registry record, then a downstream operation asserts on an impossible local controller shape instead of explaining the stale runtime authority.

## What Changes

- Add a user-facing error-diagnostics contract for maintained `houmao-mgr` commands.
- Replace known implementation-level command failures with actionable diagnostics that name the target, cause, evidence, and next action.
- Scan maintained CLI command paths for similar bare implementation exceptions, especially generic `str(exc)` conversions, assertion-backed runtime invariants, and target-mode mismatches.
- Add regression coverage so stale or degraded managed-agent targets do not surface bare Python exception class names from gateway, mail, state, prompt, interrupt, and related scoped command families.
- Keep tracebacks suppressed for normal operator use, while making the fallback for unexpected internal failures explicit enough to report and debug.

## Capabilities

### New Capabilities
- `houmao-mgr-error-diagnostics`: User-facing CLI error diagnostics for maintained `houmao-mgr` commands, including stale/degraded managed-agent target handling and internal-error fallback behavior.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/main.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, and maintained command modules under `src/houmao/srv_ctrl/commands/agents/`.
- Affected tests: `tests/unit/srv_ctrl/test_commands.py`, `tests/unit/srv_ctrl/test_managed_agents.py`, and focused command-family tests where similar implementation-level messages are found.
- No public API or storage format change is intended.
