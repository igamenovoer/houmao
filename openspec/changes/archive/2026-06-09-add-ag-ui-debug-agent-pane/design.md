## Context

The AG-UI workbench already provides direct AG-UI pane behavior: target configuration, capabilities fetch, connect/run SSE consumption, event reduction, diagnostics, and typed component rendering. Recent validation showed the GUI can render a chart when a controlled AG-UI SSE stream delivers a complete `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` sequence. The live managed-agent path still remains harder to debug because `delivered_count = 0` can come from gateway subscription/routing, stale connection state, or wrong route metadata before the GUI renderer is involved.

The new feature should give operators a controlled protocol playground inside the workbench. It should behave like a normal AG-UI target from the display side while avoiding managed-agent lifecycle, passive-server registry, tmux, credentials, or gateway queue dependencies.

## Goals / Non-Goals

**Goals:**
- Add a toolbar-opened Debug Agent pane with a side-by-side white-box sender and AG-UI display.
- Provide a host-side relay endpoint reachable from `curl` on the workbench host.
- Let internal UI sends and external `curl` sends deliver messages to the display through standard AG-UI SSE frames.
- Reuse the existing workbench AG-UI client, reducer, diagnostics, and typed component renderer path for the display.
- Support both raw AG-UI event batches and typed Houmao component convenience messages.
- Make live delivery, stored replay, and display evidence visible for debugging.
- Cover the feature with deterministic Playwright tests and screenshot evidence.

**Non-Goals:**
- Do not create a Houmao managed agent, tmux session, passive-server registry entry, or gateway sidecar for the debug agent.
- Do not change live per-agent gateway publish semantics.
- Do not let the debug pane manage real agent lifecycle, prompts, interrupts, mailboxes, credentials, or runtime state.
- Do not add a production multi-user server. The initial relay is a local development/test helper hosted by the workbench dev server.
- Do not inject rendered component state directly into React; the display must consume AG-UI events over the same client path as normal panes.

## Decisions

### Decision: Host-side debug relay, not browser-only state

The debug agent relay will run in the workbench host process, next to the existing Vite AG-UI proxy middleware. External callers can then use normal `curl` against `http://127.0.0.1:<workbench-port>/__houmao_debug_agents/...`.

Rejected alternative: browser-only state injection. This would make the Send button easy, but external `curl` could not reach it, and it would stop proving the AG-UI client/reducer path.

Rejected alternative: real Houmao managed dummy agent. That would test too much: managed launch, registry, gateway attachment, and tmux behavior. The requested feature is a protocol playground for GUI rendering and AG-UI message delivery.

### Decision: Composite pane with sender and display sides

The toolbar will open a Debug Agent pane rather than a normal agent pane. The pane owns two adjacent areas:

```text
---------------------------------------------------------------+
| Debug Agent                                                  |
+-------------------------------+-------------------------------+
| White-box sender             | AG-UI display                  |
| - mode selector              | - normal target/connect state   |
| - JSON/editor                | - transcript                    |
| - Validate / Send / Copy curl| - typed graphics renderers      |
| - publish response           | - diagnostics/raw events        |
+-------------------------------+-------------------------------+
```

The right side may reuse the `AgentSessionPanel` internals through a shared display component or a refactored common session view, but it must still open an AG-UI connection to the debug relay. The left side posts to the same relay endpoints that external callers use.

Rejected alternative: open two separate Dockview panes. It would work, but it scatters one debug agent across the layout and makes the curl target harder to discover. A composite pane keeps the sender, endpoint, and display evidence together.

### Decision: AG-UI-compatible route family per debug agent

Each debug agent gets a stable ID and thread:

```text
debug-agent-1
debug-agent-1-thread
```

The route family is:

```text
GET    /__houmao_debug_agents/status
GET    /__houmao_debug_agents/:agentId/v1/ag-ui/capabilities
POST   /__houmao_debug_agents/:agentId/v1/ag-ui/connect
POST   /__houmao_debug_agents/:agentId/v1/ag-ui/runs
POST   /__houmao_debug_agents/:agentId/v1/ag-ui/events
DELETE /__houmao_debug_agents/:agentId/v1/ag-ui/connections/:connectionId
POST   /__houmao_debug_agents/:agentId/components/:componentName
```

`connect` and `runs` both produce an SSE stream. `events` accepts already-standard AG-UI events. `components/:componentName` is a convenience route that wraps a validated typed component payload into standard AG-UI tool-call events before publishing.

The display target URL will be:

```text
http://127.0.0.1:<workbench-port>/__houmao_debug_agents/debug-agent-1/v1/ag-ui
```

### Decision: Bounded debug replay with explicit labeling

The debug relay will keep a bounded per-thread replay buffer by default so operators can run `curl` before connecting the display and still inspect the result. The response will distinguish live delivery from stored replay:

```json
{
  "status": "accepted",
  "acceptedCount": 3,
  "deliveredCount": 0,
  "storedCount": 3,
  "replay": "debug_thread_buffer"
}
```

A live-only mode will be available, either through a pane toggle or request option, so operators can reproduce gateway-like `replay: "none"` behavior.

This is intentionally different from the live gateway. The debug UI and docs must say so clearly.

### Decision: Local-only endpoint policy

The debug relay is a local development/test endpoint. It should bind through the existing workbench dev server and be reachable on the same host/port as the GUI. It should accept loopback callers by default and should not expose secrets, credentials, cookies, authorization headers, or persisted stream payloads.

The relay should bound payload size, event count, connection count, and replay buffer length. It should validate standard AG-UI event shape and local sequence constraints before delivery.

### Decision: Persistence boundary mirrors normal panes

The workbench may persist debug-agent pane layout, debug-agent ID, target URL, thread ID, and editor options. It must not persist posted event batches, raw stream events, typed component payloads, transcript content, rendered graphics, or external caller request bodies by default.

## Risks / Trade-offs

- Debug replay differs from live gateway semantics -> Label replay mode in the UI, publish responses, and docs; include a live-only toggle and test.
- The relay could accidentally become a second production gateway -> Keep the route prefix workbench-specific, document it as a dev/test surface, and avoid passive-server registry publication.
- Raw event posting can carry unsafe payloads -> Validate AG-UI event shape, keep typed renderers safe, and preserve current renderer behavior that does not inject raw HTML/SVG for typed components.
- Composite pane may duplicate session panel code -> Prefer extracting shared AG-UI display logic instead of forking the reducer/rendering implementation.
- External curl cannot reach the browser if the Vite dev server is not running -> Document that the debug relay runs in the workbench host process and expose `/__houmao_debug_agents/status`.
- Multiple debug panes can collide on IDs or threads -> Generate stable unique pane IDs and thread IDs, and scope relay subscriptions by debug-agent ID plus route metadata.

## Migration Plan

No stored runtime data migration is required. Existing workbench local storage should continue to load. New debug-agent pane records should be sanitized so older or unknown records fall back safely, and closing a debug pane should detach only its debug relay connection.

## Open Questions

- Should the component convenience route validate payloads using a duplicated TypeScript schema, a generated JSON Schema bundle, or only the renderer-side validation initially?
- Should replay be on by default for all debug agents, or should the first pane start in live-only mode to match gateway behavior?
- Should the debug endpoint be enabled unconditionally in dev mode, or guarded by an environment variable for extra clarity?
