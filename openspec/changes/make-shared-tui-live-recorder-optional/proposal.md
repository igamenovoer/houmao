## Why

The shared TUI live-watch demo currently starts terminal-recorder passive capture every time `start` launches a session, even when the operator only wants an interactive smoke test. That default adds extra tmux sessions, artifacts, and lifecycle overhead to the common path, while recorder evidence is primarily needed for replay debugging and offline analysis.

## What Changes

- Change shared-TUI live-watch startup so recorder capture is optional instead of mandatory.
- Make the default live-watch path launch the tool session and dashboard without starting terminal-recorder.
- Add an explicit live-watch option in the demo-owned config and operator-facing commands to enable recorder-backed capture when replay debugging is needed.
- Preserve recorder-backed live replay/finalization behavior when the operator explicitly enables recorder capture.
- **BREAKING**: `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start` no longer creates recorder artifacts by default.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shared-tui-tracking-live-watch`: change live-watch requirements so recorder-backed observation is optional and default interactive runs can proceed without terminal-recorder.
- `shared-tui-tracking-demo-configuration`: change the demo config contract so live-watch recorder enablement is an explicit, documented launch/debug control rather than an always-on behavior.

## Impact

- Affected code: `src/houmao/demo/shared_tui_tracking_demo_pack/live_watch.py`, demo config parsing/schema, driver CLI wiring, and related tests.
- Affected operator surfaces: `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start`, `inspect`, `stop`, and the demo config/docs.
- Affected artifacts: live-watch runs will only create terminal-recorder roots and replay-debug artifacts when recorder capture is enabled.
