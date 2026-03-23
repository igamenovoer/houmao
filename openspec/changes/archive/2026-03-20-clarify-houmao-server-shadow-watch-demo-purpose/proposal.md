## Why

The Houmao-server dual shadow-watch demo was originally framed around shadow-parser and lifecycle validation at the demo layer. Since `houmao-server` now owns the authoritative live tracked-state contract, that framing is stale and risks confusing operators about where tracking semantics actually live.

## What Changes

- Reframe the demo as a server-state observer for live interactive Claude/Codex sessions rather than as a second tracker or parser-validation surface.
- Update the demo monitor to present `houmao-server` state more faithfully, including server-owned stability and lifecycle-authority semantics.
- Remove or rename demo-facing wording and labels that imply demo-owned tracking semantics when they actually reflect server-owned configuration or payloads.
- Update the README, autotest guide, and demo profile copy so the operator workflow is described as “interactively prompt the tools and watch the server-tracked state change.”

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-server-dual-shadow-watch-demo`: clarify that the pack consumes and visualizes server-owned tracked state, and tighten the monitor/README contract around server-owned stability, lifecycle authority, and interactive prompting workflow

## Impact

- Demo-facing code under `src/houmao/demo/houmao_server_dual_shadow_watch/`
- Demo-pack assets under `scripts/demo/houmao-server-dual-shadow-watch/`
- Unit tests for the server-backed demo monitor and driver
- OpenSpec/demo documentation that currently implies demo-local tracking behavior
