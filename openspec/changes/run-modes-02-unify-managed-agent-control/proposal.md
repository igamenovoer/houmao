# Proposal

## Why

The manager, gateway, passive server, and AG-UI infer operations separately from backend names. An unfamiliar backend can acquire terminal observation by default, and a successful queue insertion can be mistaken for delivery to an agent.

## What Changes

- Route lifecycle, control, communication, and observation through the same owner-bound runtime operations for an existing managed agent. Keep first launch and offline recovery reachable through the manager.
- Expose mode, supported operations, readiness, and the available evidence of handoff or completion through existing authorized entrypoints. Report uncertainty when native evidence is incomplete.
- Dispatch mail wakeups, ordinary plugin events, and operator prompts with their existing admission policies. Preserve authenticated access, public handoff-only outcomes, and channel-specific mail storage.
- Use existing headless CLI, TUI, and DSH Web adapters as the first end-to-end conformance cases. Add service projections that future adapters can implement.

## Capabilities

### New Capabilities

- `managed-agent-control` defines shared operation semantics, capability reporting, and conformance across managed modes.

### Modified Capabilities

- `agent-gateway` uses declared operations and the saved owner for control dispatch.
- `houmao-mgr-registry-discovery` routes qualified mode/backend pairs in the recorded execution context.
- `managed-agent-detailed-state` exposes mode-specific evidence and service detail.
- `passive-server-tui-observation` chooses the terminal observer only for a declared terminal UI.
- `per-agent-ag-ui-run-streaming` uses correlated native events for service runs and honest Web observation.

## Impact

Affects the runtime controller, per-agent gateway, manager commands, passive discovery/proxy, AG-UI mapper, and API consumers. Existing public and protected gateway paths keep their authorization and disclosure rules.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-01-introduce-managed-agent-run-modes`. Changes 03, 04, and 07 can use this contract independently.
