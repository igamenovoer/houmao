## Why

The repository already has a CAO-backed interactive full-pipeline demo, but it does not show the current Houmao-managed pair boundary where startup goes through `houmao-srv-ctrl` and all live interaction goes through `houmao-server` HTTP endpoints. A dedicated replacement demo is needed now so operators and maintainers have one concrete, repeatable walkthrough for the supported `houmao-server + houmao-srv-ctrl` split.

## What Changes

- Add a new repo-owned interactive demo pack that installs one tracked compatibility profile into a demo-owned `houmao-server` and launches one Claude or Codex TUI session through `houmao-srv-ctrl`.
- Rely on the pair-managed startup path where `houmao-srv-ctrl launch` materializes delegated runtime artifacts and registers the launched session with `houmao-server`.
- Drive follow-up interaction through direct `houmao-server` API calls instead of `houmao-srv-ctrl` or `houmao-cli` runtime control commands.
- Preserve the operator ergonomics of the older CAO demo pack: start, inspect, send-turn, interrupt, verify, clean stop, persisted demo state, and `launch_alice.sh`.
- Document the v1 server-route split used by the demo: managed-agent routes for prompt, interrupt, and state inspection, plus server HTTP teardown through the existing compatible session surface.
- Keep raw control-input parity out of v1 so the demo does not introduce a `send-keys` equivalent before `houmao-server` has a dedicated server-side route for it.

## Capabilities

### New Capabilities
- `houmao-server-interactive-full-pipeline-demo`: A repo-owned demo pack that launches a `houmao-server` managed TUI session through `houmao-srv-ctrl` and then interacts with it through direct `houmao-server` HTTP endpoints.

### Modified Capabilities

## Impact

- Affected code: new demo package under `src/houmao/demo/`, tracked compatibility-profile assets under `scripts/demo/`, new shell wrappers under `scripts/demo/`, and demo-specific tests under `tests/unit/demo/` and `tests/integration/demo/`
- Affected docs: demo README, operator-facing reference docs, and any migration guidance that currently points interactive walkthroughs only at the CAO demo
- Affected systems: `houmao-srv-ctrl` install and launch flow, `houmao-server` registration and managed-agent routes, tracked terminal inspection routes, and demo-owned verification/reporting
