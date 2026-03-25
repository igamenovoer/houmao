## Why

The current CAO-compatible startup path relies on several fixed timeout values and one fixed Codex warmup delay across the pair client and the Houmao-owned compatibility control core. Those defaults are reasonable as a baseline, but operators cannot override them through supported user-facing configuration, which makes slow but healthy environments brittle and forces local patching when startup latency exceeds the baked-in budgets.

## What Changes

- Split pair client CAO-compatible timeout handling into lightweight request timeouts and heavyweight create-operation timeouts, with an explicit longer default budget for session and terminal creation.
- Add supported user-facing override paths for pair client CAO-compatible HTTP timeouts instead of requiring local code patches.
- Add supported user-facing override paths for Houmao-owned CAO compatibility startup waits, including shell-readiness wait, provider-readiness wait, polling cadences, and the Codex warmup delay, while preserving the current server-side defaults unless the operator overrides them.
- Define clear precedence for timeout configuration so CLI flags, environment variables, and config defaults resolve predictably.
- Document which timeout knobs affect lightweight pair requests versus long-running CAO-compatible session and terminal creation.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `cao-rest-client-contract`: The CAO-compatible client requirements will change so operational timeout budgets remain defaulted but become user-overrideable through supported configuration, including a distinct longer default budget for heavyweight create operations.
- `houmao-cao-control-core`: The Houmao-owned compatibility control core requirements will change so synchronous compatibility startup waits and warmup delays remain defaulted but become user-overrideable through supported server configuration.
- `houmao-srv-ctrl-cao-compat`: The pair-compatible launch CLI requirements will change so session-backed compatibility launch surfaces expose additive timeout override options for operators without changing the native headless contract.

## Impact

- Affected code:
  - `src/houmao/cao/rest_client.py`
  - `src/houmao/server/client.py`
  - `src/houmao/srv_ctrl/commands/common.py`
  - `src/houmao/srv_ctrl/commands/launch.py`
  - `src/houmao/srv_ctrl/commands/cao.py`
  - `src/houmao/server/config.py`
  - `src/houmao/server/commands/common.py`
  - `src/houmao/server/commands/serve.py`
  - `src/houmao/server/control_core/core.py`
  - `src/houmao/server/control_core/provider_adapters.py`
  - `src/houmao/server/control_core/tmux_controller.py`
- Affected APIs and CLIs:
  - `houmao-mgr launch`
  - `houmao-mgr cao launch`
  - `houmao-server serve`
  - CAO-compatible session and terminal creation through `/cao/*`
- Affected systems:
  - pair-managed detached TUI launch
  - pair-managed CAO-compatible runtime startup
  - operator documentation for timeout tuning
