## Why

The shared tracked-TUI demo pack currently relies too heavily on in-process cleanup and late-written metadata. `recorded-capture` only reaps its tmux session from a `finally` block after startup has already crossed a leak window, and the durable capture manifest is written after that window instead of before it.

When startup fails or the operator loses the active run context, stale `shared-tui-*` and `HMREC-*` tmux sessions can remain without a durable ownership trail that later cleanup can trust. The demo pack needs explicit session bookkeeping so cleanup can recover workflow-owned resources from run artifacts and live tmux metadata instead of depending on one uninterrupted happy path.

## What Changes

- Persist run-local session-ownership bookkeeping before and as workflow-owned tmux or recorder resources are created, rather than only after a run completes.
- Publish demo-owned session ownership pointers into tmux session environment so later cleanup can rediscover the run manifest and owned-role metadata from live tmux state.
- Add shared recovery logic that reconciles run manifests with live tmux sessions and can identify workflow-owned tool, dashboard, and recorder sessions even after partial startup failure.
- Add an operator-facing cleanup command that can reap workflow-owned stale tmux resources by targeted run root or by demo-owned ownership markers.
- Harden `recorded-capture` so failures between tmux launch and ordinary manifest finalization still leave enough metadata for later cleanup.
- Extend live-watch lifecycle handling so `inspect`, `stop`, and failed-start cleanup use the same durable ownership metadata instead of assuming all workflow state survived in memory.
- Update demo documentation to explain how workflow-owned tmux resources are discovered and reaped.

## Capabilities

### New Capabilities
- `shared-tui-tracking-demo-session-ownership`: Durable ownership metadata, tmux-published recovery pointers, and orphan-discovery rules for workflow-owned shared tracked-TUI demo sessions.

### Modified Capabilities
- `shared-tui-tracking-live-watch`: Live-watch lifecycle commands and failed-start cleanup use durable session bookkeeping and recovered tmux ownership metadata when resolving workflow-owned sessions.

## Impact

- Affected code: `src/houmao/demo/shared_tui_tracking_demo_pack/live_watch.py`, `src/houmao/demo/shared_tui_tracking_demo_pack/recorded.py`, `src/houmao/demo/shared_tui_tracking_demo_pack/tooling.py`, `src/houmao/demo/shared_tui_tracking_demo_pack/models.py`, and the demo driver/CLI path.
- Affected docs: `scripts/demo/shared-tui-tracking-demo-pack/README.md` and `scripts/demo/shared-tui-tracking-demo-pack/CONFIG_REFERENCE.md`.
- Affected tests: unit coverage for recorded-capture startup failure windows, live-watch stop/inspect recovery, and tmux ownership discovery from persisted manifest plus tmux session environment.
- Related system boundary: tmux session environment publication and lookup should align with existing repo patterns for durable session discovery rather than inventing an unrelated cleanup-only mechanism.
