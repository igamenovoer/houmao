# Design

## Context

Manager commands can enter the owner execution context and load a runtime controller. The gateway already enforces authentication and different admission policies for ordinary and deferred work. Passive observation and AG-UI also select paths by backend or surface. These choices currently have separate fallbacks. [Gateway service](../../../src/houmao/agents/realm_controller/gateway_service.py), [passive observation](../../../src/houmao/passive_server/observation.py), and [AG-UI runtime](../../../src/houmao/ag_ui/runtime.py).

## Goals / Non-Goals

Give an operator and an authenticated client the same interpretation of an agent's identity, readiness, operations, and receipts. Keep ordinary project birth and owner-side recovery usable with a detached gateway. Each protected gateway action stays within its existing authorization and public disclosure contract.

## Decisions

### Keep Runtime Ownership in the Execution Context

`houmao-mgr project agents launch` creates the owner. Reuse change 01's manifest schema 6, managed registry schema 5, and executor locator schema 2. Owner-side describe already checks the manifest before returning the saved mode, generation, and surface. The gateway must check the same identity before selecting or refreshing its adapter. Owner-only lifecycle actions retain their authorized manager entrypoints while the gateway starts, stops, or loses its listener. [Runtime controller](../../../src/houmao/agents/realm_controller/runtime.py) and [gateway access proof](../../../src/houmao/agents/realm_controller/gateway_access_runtime.py).

### Distinguish Admission From Execution

Keep the existing durable request storage for immediate and explicitly deferred operations. Manager access follows the saved OS execution binding. Protected gateway requests follow enrolled HTTP access. Both call the same owner-side admission and native evidence rules after authorization. This preserves owner CLI access for an agent with an enrolled gateway and no configured CLI admin signer. The shared reservation binds the active registry generation, canonical manifest path, and request identity. It remains attributable after a caller or the gateway disconnects. An ambiguous outcome does not trigger a second dispatch. Manager lifecycle operations remain available through the owner.

Ordinary mail wakeups and plugin delivery request immediate dispatch under their current policies. Verify generation and native identity at the final write. Record queued, handed off, terminal, failed, or uncertain evidence with its available request, native turn, origin, and timestamp. Reuse the queue and event storage and the existing native attempt artifacts. Durable inbox storage can succeed independently of a refused wakeup.

### Describe Each Mode Through the Same Operations

Adapters report support for semantic prompt, interrupt, state/events, usage and lifecycle, alongside optional raw keys, human handoff, and native refresh. Only a verified terminal surface supplies raw keys. Headless uses the active attempt and persisted turn artifacts. TUI uses its existing provider tracker and terminal handoff evidence. Web uses a verified host/session and operation-correlated native observations. Service gets a typed owner, connection, session, and request projection, exercised by a stub until its native adapters become selectable. Missing evidence stays unknown.

The maintained passive server preserves the raw TUI response at `/houmao/agents/{agent_ref}/state` and `/state/detail` for verified terminal agents. Those routes use structured mode-specific state for headless, service, and Web. Its `/managed-state` and `/managed-state/detail` routes retain their curated response envelope. The curated TUI detail links to the passive server's actual raw route. AG-UI uses request-correlated evidence for output and terminal outcomes. Shared Web activity stays attributable to the host or browser and cannot settle an AG-UI run. [Managed detail requirements](../../specs/managed-agent-detailed-state/spec.md).

### Make Conformance Observable Through Public Surfaces

Exercise manager and authenticated gateway against the same agent, with a competing ordinary delivery, detach/reattach, owner stop while the gateway is down, and execution-context routing. Use self-hosted `Qwen/Qwen3.8-27B-FP8` with the maintained fixture and verified private tmux sockets established in 01. Reuse Kimi for one-shot and TUI cases and DSH for Web on this endpoint. Each observation reports the available native evidence. Add future providers by implementing these operations and passing their mode-specific evidence cases.

## Risks / Trade-offs

- A second mutating path could bypass immediate admission. Drive the actual manager and protected gateway routes concurrently against one owner and assert a single native handoff.
- Observation can expose private provider access. Restrict public handoff to the sanitized human reference and keep detailed control behind current authorization. Treat stale or unreachable owner routes as such.

## Migration Plan

Introduce the owner-bound contract and adapt existing one-shot, TUI, and DSH Web controls before enabling the new pairs. Check passive routes, AG-UI, mail, plugins, and execution locators against those real entrypoints. Coordinate the initial release with 01, 03, and 04. Release rollback follows 01's fresh-launch boundary.
