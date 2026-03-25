## Why

`houmao-mgr server start` currently behaves like `houmao-server serve`: it occupies the foreground and gives no pair-native startup summary beyond uvicorn logs. That makes the recommended server lifecycle entrypoint awkward for ordinary operator use, where the common intent is to start the server, get one clear status result, and continue using the terminal for follow-up `houmao-mgr` commands.

## What Changes

- Change `houmao-mgr server start` so the default behavior starts `houmao-server` as a detached background process instead of blocking the invoking terminal.
- Add a `--foreground` option to preserve the current foreground startup mode when an operator explicitly wants the server attached to the current terminal.
- Make `houmao-mgr server start` print a pair-native startup status payload that reports what was started, the resolved server URL, whether startup succeeded, and enough process/runtime metadata for operators to confirm ownership.
- Define failure reporting for detached startup so the command exits cleanly with an explicit unsuccessful startup result rather than leaving the operator to infer failure from missing logs.
- **BREAKING**: change the default invocation posture of `houmao-mgr server start` from foreground-blocking to background-detached.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-server-group`: change the `server start` lifecycle contract so detached startup is the default, `--foreground` is the explicit foreground mode, and startup returns a status-oriented operator result.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/server.py`
  - shared server startup helpers used by `houmao-mgr` and `houmao-server`
  - startup/status models or utilities for detached process ownership and reporting
- Affected tests:
  - unit and integration coverage for `houmao-mgr server start`
  - CLI-shape and lifecycle tests that currently assume foreground default behavior
- Affected docs:
  - pair usage docs and CLI reference examples for `houmao-mgr server start`
