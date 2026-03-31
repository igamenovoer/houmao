## Why

The supported `single-agent-mail-wakeup` demo already proves the end-to-end wake-up flow, but its stepwise/manual mode is still closer to a test harness than an operator-facing demo. After `start`, users can watch the agent TUI directly, yet the pack does not expose a first-class way to re-attach to the live session, observe the gateway console without entering tmux manually, or manage the gateway mail notifier while the demo is running.

## What Changes

- Extend the stepwise/manual command surface of `scripts/demo/single-agent-mail-wakeup/` with operator-facing commands for `attach`, `send`, `watch-gateway`, and `notifier ...`.
- Make stepwise `start` attach the gateway in an auxiliary tmux window so the demo can expose the live gateway console through a demo-owned `watch-gateway` wrapper without requiring the user to inspect tmux window metadata directly.
- Expose gateway mail-notifier lifecycle controls through the demo pack, including status, enable/on, disable/off, and interval updates.
- Revise the README and stepwise workflow guidance to teach the interactive flow as `start -> attach -> watch-gateway -> send -> verify -> stop`.
- Keep the existing `auto` and `matrix` flows stable and non-interactive; the enhancement only broadens the stepwise/manual operator surface.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `single-agent-mail-wakeup-demo`: Expand the supported stepwise command surface and require watchable foreground gateway behavior plus demo-owned notifier controls.

## Impact

- Affected code includes the demo pack wrapper, the `single_agent_mail_wakeup` driver/runtime helpers, persisted control/log artifact handling, and focused demo unit coverage.
- Affected operator surfaces include `scripts/demo/single-agent-mail-wakeup/README.md` and the supported command model printed by the demo runner.
- The change reuses existing gateway attach and mail-notifier operations; it does not introduce a new transport or a new gateway protocol surface.
