# Design

## Context

Manager commands can enter the owner execution context and load a runtime controller. The gateway already enforces authentication and different admission policies for ordinary and deferred work. Passive observation and AG-UI also select paths by backend or surface. These choices currently have separate fallbacks. [Gateway service](../../../src/houmao/agents/realm_controller/gateway_service.py), [passive observation](../../../src/houmao/passive_server/observation.py), and [AG-UI runtime](../../../src/houmao/ag_ui/runtime.py).

## Goals / Non-Goals

Give an operator and an authenticated client the same interpretation of an agent's identity, readiness, operations, and receipts. Keep ordinary project birth and owner-side recovery usable with a detached gateway. Each protected gateway action stays within its existing authorization and public disclosure contract.

## Decisions

### Keep Runtime Ownership in the Execution Context

`houmao-mgr project agents launch` creates the owner. Post-launch manager commands resolve the registry record or execution locator, enter its saved route, and verify generation before reading owner files. The gateway binds to that same owner. Prompt, interrupt, inspect, and supported communication callbacks use shared implementations. Owner-only lifecycle actions retain their authorized manager entrypoints. Making the gateway the parent process would couple a client-facing restart to provider cleanup. [Runtime controller](../../../src/houmao/agents/realm_controller/runtime.py) and [gateway access proof](../../../src/houmao/agents/realm_controller/gateway_access_runtime.py).

### Distinguish Admission From Execution

Keep the existing durable gateway queue for requests that authorize deferred execution. Ordinary mail wakeups and plugin delivery request immediate dispatch under their current policies. Verify agent generation and native execution at the final write, and serialize competing manager/gateway dispatch at the owner. Record queued, handed off, terminal, failed, or uncertain evidence with its available request, native turn, origin, and timestamp. Enqueue, subprocess creation, TUI input, and a live HTTP socket each establish different facts. Durable inbox storage can succeed independently of a refused wakeup.

### Describe Each Mode Through the Same Operations

Adapters report support for semantic prompt, interrupt, state/events, usage and lifecycle, alongside optional raw keys, human handoff, and native refresh. Headless uses the active attempt and persisted terminal artifacts. TUI uses its existing provider tracker and terminal route. Service projects native connection, session, and request evidence. Web uses a verified host/session and native observations. Missing evidence stays unknown. Passive compact/detail and AG-UI consume these projections, keep TUI raw detail canonical, and avoid a generic terminal fallback. [Managed detail requirements](../../specs/managed-agent-detailed-state/spec.md).

### Make Conformance Observable Through Public Surfaces

Exercise manager and authenticated gateway against the same agent, with a competing ordinary delivery, detach/reattach, owner stop while the gateway is down, and execution-context routing. Use each incumbent adapter's native observation guarantee. Add future providers by implementing these operations and passing their mode-specific evidence cases. A uniform transport or a global capability list would promise actions a native provider cannot perform.

## Risks / Trade-offs

- A second mutating path could bypass immediate admission. Drive the actual manager and protected gateway routes concurrently against one owner and assert a single native handoff.
- Observation can expose private provider access. Restrict public handoff to the sanitized human reference and keep detailed control behind current authorization. Treat stale or unreachable owner routes as such.

## Migration Plan

Introduce the owner-bound contract and adapt existing one-shot, TUI, and DSH Web controls before enabling the new pairs. Check passive routes, AG-UI, mail, plugins, and execution locators against those real entrypoints. Coordinate the initial release with 01, 03, and 04. Release rollback follows 01's fresh-launch boundary.
