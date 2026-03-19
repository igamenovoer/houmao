## Why

The existing dual shadow-watch demo proves useful for manual parser and lifecycle validation, but it still establishes its truth from raw CAO polling plus a demo-local parser and tracker. Now that `houmao-server` and `houmao-srv-ctrl` exist as the supported public pair, the repository needs an equivalent demo that validates the Houmao-owned path directly instead of teaching a second control-plane authority. It also needs to be shaped for hack-through-testing, with one clear interactive operator journey, fast blocker discovery, and preserved evidence rather than an implementation-first demo that becomes testable later.

## What Changes

- Add a new standalone demo pack under `scripts/demo/` for a Houmao-server-backed dual shadow-watch workflow.
- Provision the same projection-oriented dummy-project fixture into isolated per-agent workdirs for Claude and Codex.
- Define one canonical interactive operator path for the demo: preflight, start, attach to both agent TUIs plus the monitor, observe live state transitions, inspect, and stop.
- Start a demo-owned `houmao-server`, then launch one Claude session and one Codex session through `houmao-srv-ctrl launch` in the supported `houmao-server + houmao-srv-ctrl` pair.
- Move the live monitor to consume Houmao-owned terminal state and transition routes from `houmao-server` instead of polling CAO terminal output and re-running the parser stack in the demo process.
- Extend the official server-owned tracking contract with the lifecycle timing and stalled-state semantics needed to preserve the current demo's validation surface without reintroducing demo-local tracking authority.
- Add fail-fast preflight checks, bounded timeout behavior, and deterministic artifact locations so interactive testing surfaces real blockers quickly.
- Add design-phase HTT case plans under the change plus a planned implemented `autotest/` layout for one automatic preflight/lifecycle case and one interactive state-validation case.
- Persist server-consumer monitor evidence and document the new operator workflow, prerequisites, and public-surface boundary clearly.

## Capabilities

### New Capabilities
- `houmao-server-dual-shadow-watch-demo`: Standalone operator demo that starts a demo-owned `houmao-server`, launches Claude and Codex through `houmao-srv-ctrl`, and visualizes server-owned live tracking side by side.

### Modified Capabilities
- `official-tui-state-tracking`: extend the server-owned tracked-state contract with lifecycle timing and stalled-state information so consumer demos can preserve the existing manual-validation semantics without recomputing them locally.

## Impact

- New demo-pack files under `scripts/demo/houmao-server-dual-shadow-watch/`
- New demo package modules under `src/houmao/demo/houmao_server_dual_shadow_watch/`
- New change-owned HTT test plans under `openspec/changes/add-houmao-server-dual-shadow-watch-demo/testplans/`
- Planned implemented autotest surfaces under `scripts/demo/houmao-server-dual-shadow-watch/autotest/`
- Server tracking models and reducers under `src/houmao/server/`
- Houmao server client/query surfaces used by the demo monitor
- Demo and server tests plus operator-facing documentation for the new workflow
