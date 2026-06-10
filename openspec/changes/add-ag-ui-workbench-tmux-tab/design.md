## Context

The AG-UI workbench currently has three pane kinds: `operator`, `agent`, and `debug-agent`. The `operator` pane uses the same AG-UI mechanics as ordinary agent panes and has no real operator-specific protocol behavior. It is a stub that adds another concept without adding capability.

Agent and Debug Agent panes speak AG-UI over HTTP/SSE and render reduced AG-UI event state. They do not expose the underlying tmux terminal that many Houmao managed agents use for TUI execution.

The local `extern/tracked/tailmux` reference shows a useful browser-terminal pattern: xterm.js in the browser talks over WebSocket to a host-side Node process, and that process uses `node-pty` to attach to tmux. The workbench already has host-side Vite plugins for the AG-UI proxy and Debug Agent relay, so the tmux bridge can fit into the same local development-server boundary without launching a separate Tailmux app.

The workbench should remove the dedicated Operator tab. To act as an operator, a user can either attach a tmux tab and directly control any tmux session through its TUI, or mark one ordinary Houmao agent pane as the operator pane for orientation. That operator marker is UI metadata only in this change.

A tmux-controlled agent does not receive a workbench prompt body, so it also does not receive any GUI-appended context such as the current AG-UI thread. The gateway needs a small Houmao extension that records recent destination state, so an agent using `houmao-mgr internals ag-ui` from its TUI can publish graphics without guessing routing fields.

## Goals / Non-Goals

**Goals:**

- Add a docked `tmux` tab kind to the workbench.
- Remove the dedicated default `operator` tab and stop treating `operator` as a first-class pane kind.
- Allow one ordinary Houmao agent pane to be flagged as the operator pane.
- Let users list local tmux sessions, search them quickly, and attach one session per tmux tab.
- Use Fuse.js for fuzzy session search by tmux name and Houmao agent metadata.
- Let users filter the picker to sessions that correspond to Houmao managed agents.
- Attach read-write by default and support explicit read-only attachment.
- Enforce read-only at both the browser terminal and host bridge.
- Keep tmux attachment lifecycle separate from Houmao agent lifecycle.
- Persist only non-sensitive tmux tab configuration and selected session metadata.
- Maintain gateway-local last-bound AG-UI thread state for the actively viewed workbench agent pane.
- Maintain gateway-local last-sent AG-UI thread state refreshed by successful gateway publishes to concrete thread destinations.
- Let Houmao gateway AG-UI publish resolve omitted routing through message-specified thread, last-sent thread, last-bound thread, then a Houmao-defined default sink.
- Teach tmux-controlled agents through the maintained AG-UI system skill how to omit routing safely and interpret default-sink warnings or no-delivery results.

**Non-Goals:**

- Do not add special AG-UI routing, privileges, prompt fan-out, or gateway behavior for the operator marker.
- Do not make last-bound-thread, last-sent-thread, or the default sink part of the AG-UI standard; they are Houmao gateway extensions.
- Do not make destination fallback state durable across gateway restarts or use it for event replay.
- Do not let passive background watchers change the bound publish target.
- Do not expose the internal default sink thread name to agents as a route they should target.
- Do not add tmux session creation, kill, rename, window management, pane splitting, or copy-mode controls in this change.
- Do not route tmux terminal bytes through AG-UI.
- Do not make the packaged Python wheel serve the workbench or tmux bridge.
- Do not persist terminal scrollback, terminal input, credentials, or raw terminal content.

## Decisions

### Retire the Dedicated Operator Pane

The workbench should no longer create an `operator` panel on first load or when the layout becomes empty. The default empty workspace can show Dockview's empty-group overlay until the user opens an agent, Debug Agent, or tmux tab.

The persisted pane-kind model should stop creating new `operator` records. During storage sanitization, legacy `operator` pane records may be dropped or converted to ordinary `agent` panes if conversion can preserve a valid AG-UI target. The implementation should favor a clear forward model over compatibility shims because this repository is still in active unstable development.

Alternative considered: keep the operator pane hidden but available. That preserves the stub and keeps the model more confusing. Removing the default operator pane gives the workbench a cleaner rule: all AG-UI agent interaction uses ordinary agent panes.

### Add a UI-Only Operator Marker on Agent Panes

Store operator designation as a single optional pane id, for example:

```ts
interface WorkbenchStorage {
  operatorPaneId?: string;
}
```

Only ordinary Houmao agent panes are eligible for the marker. A pane is Houmao-backed when its target source is a discovered Houmao agent. The marker does not alter AG-UI request bodies, target resolution, watched-target behavior, gateway routing, event caching, prompts, or tmux behavior. If the marked pane closes or stops being a Houmao-backed agent pane, the workbench clears the marker.

Alternative considered: make operator a separate role-bearing pane kind. That recreates the same conceptual problem as the current `operator` pane. A global marker keeps the role explicit while preserving the ordinary agent-pane behavior.

### Add Gateway Destination State

Add gateway-local Houmao AG-UI destination state for the currently foreground workbench thread and the last concrete thread that received a gateway publish. The state is volatile process memory and starts empty on each gateway start:

```ts
interface AgUiDestinationState {
  lastBoundThread: {
    status: "empty" | "bound";
    threadId: string | null;
    updatedAtUtc?: string;
    source?: "gui_connect" | "gui_view_change" | "manual";
  };
  lastSentThread: {
    status: "empty" | "sent";
    threadId: string | null;
    updatedAtUtc?: string;
    source?: "explicit" | "event" | "last_sent" | "last_bound";
  };
}
```

Expose the state through Houmao extension routes, for example:

```text
GET    /v1/ag-ui/bindings
GET    /v1/ag-ui/bindings/last-thread
PUT    /v1/ag-ui/bindings/last-thread
DELETE /v1/ag-ui/bindings/last-thread
```

The workbench should bind only the actively viewed GUI target. It sets the binding when an agent pane becomes the foreground/viewed pane for that gateway or when the user changes the viewed thread in that pane. Background watchers, passive reconnects, hidden panes, and client event-cache listeners must not overwrite the binding merely because they opened an SSE stream.

The gateway owns `lastSentThread`. It refreshes that value whenever an AG-UI publish resolves to a concrete non-sink thread destination and the gateway sends the event batch through its normal AG-UI publish path. A publish that falls through to the default sink does not replace `lastSentThread`.

Alternative considered: have agents infer a thread from the gateway's active connections. That is ambiguous when multiple workbench panes, debug panes, or background watchers are connected to the same gateway. Explicit GUI-maintained binding plus gateway-maintained last-sent state keeps fallback deterministic.

### Resolve Omitted Publish Routing Through Last-Sent, Last-Bound, Then Sink

Houmao gateway AG-UI event publishing should keep explicit routing authoritative. The route resolution order is:

1. Destination specified by the publish request or event batch, including explicit `connectionId`, explicit `threadId` plus optional `runId`, or a single consistent event-level `threadId`.
2. Gateway `last-sent-thread`, if present.
3. Gateway `last-bound-thread`, if present.
4. Gateway default sink.

The default sink is a Houmao-defined destination that is not exposed to the agent as a thread name. The current sink behavior is to accept the valid event batch, write a gateway log entry that includes safe routing metadata, perform no GUI fan-out, and return a publish warning such as `default_sink_due_to_no_destination`. This makes the failure visible without requiring the agent to invent or know a fallback thread id.

When a publish resolves to a real thread through the first three steps, the gateway refreshes `lastSentThread` to that concrete thread. This includes publishes that use the previous `lastSentThread` fallback. The gateway does not refresh `lastSentThread` to the internal sink.

The CLI can then support this flow from a tmux-controlled agent:

```text
houmao-mgr internals ag-ui events render houmao.chart.bar --input chart.json --output events.json
houmao-mgr agents gateway ag-ui publish --input events.json
```

The explicit route flags remain available and continue to override gateway destination fallback:

```text
houmao-mgr agents gateway ag-ui publish --thread-id agent-1-thread --input events.json
```

Alternative considered: return a no-send error when no bound thread exists. That is precise, but it loses a useful diagnostic trail and makes agent behavior branch harder. The default sink gives the gateway one consistent Houmao-defined outcome while still warning the agent that no GUI destination was available.

### Add a Separate `tmux` Pane Kind

Add `tmux` to the existing pane-kind model and map it to a new `TmuxTabPanel` component. The pane record stores a tmux config object, for example:

```ts
type PaneKind = "agent" | "debug-agent" | "tmux";

interface TmuxTabConfig {
  sessionName?: string;
  mode: "read-write" | "read-only";
  houmaoOnly: boolean;
}
```

Alternative considered: convert the old operator pane into a terminal attachment pane. That would blur AG-UI semantics with terminal attachment semantics. Keeping tmux as its own pane lets the GUI show AG-UI canvas state and raw TUI state side by side.

### Implement the Tmux Bridge as a Vite Plugin

Add a workbench-local Vite plugin, for example `scripts/tmuxPlugin.ts`, with these local routes:

```text
GET /__houmao_tmux/status
GET /__houmao_tmux/sessions
WS  /__houmao_tmux/attach
```

`GET /sessions` lists local tmux sessions with stable metadata such as session name, window count, attached status, and created time. `WS /attach` accepts an initial JSON message with the target session, mode, and terminal size. The plugin uses `node-pty` to run `tmux attach-session -t <session>` for read-write and `tmux attach-session -r -t <session>` for read-only.

Alternative considered: run the Tailmux app as a separate process and embed or link to it. That duplicates routing, layout, and state management outside the workbench and makes local setup harder. A Vite plugin keeps the terminal bridge behind the same loopback origin as the existing workbench dev server.

### Classify Houmao Sessions by Joining Tmux and Passive-Server Discovery

The browser combines raw tmux session data from `/__houmao_tmux/sessions` with the passive server's existing `/houmao/agents` discovery response. A tmux session is classified as a Houmao agent session when its session name matches a discovered agent's `tmux_session_name`.

This keeps registry parsing in the existing Python passive server and avoids reimplementing shared-registry rules in the Node plugin. If the passive server is unavailable, the picker can still list raw tmux sessions, but the Houmao-only filter has no matched sessions and should show a clear empty/error state.

Alternative considered: have the Node plugin parse the shared registry or tmux environment variables directly. That creates a second source of truth for Houmao agent classification and risks drifting from passive-server discovery.

### Use Fuse.js for Picker Search

The session picker indexes the combined row model with Fuse.js. Search keys should include tmux session name plus any matched Houmao metadata:

```text
sessionName
houmao.agentName
houmao.agentId
houmao.tool
houmao.backend
houmao.generationId
```

The Houmao-only checkbox filters before or after search, but the visible result must satisfy both constraints when both are active.

Alternative considered: simple substring filtering. It is easy but weaker for long generated agent names and generation ids. Fuse.js gives predictable local fuzzy search without involving a server request.

### Enforce Read-Only on Both Sides

Read-only mode is not just a visual state. The browser terminal disables stdin and does not send input messages. The WebSocket bridge also records the attachment mode and rejects or ignores any `input` message for a read-only socket.

Alternative considered: rely only on `tmux attach-session -r`. That protects tmux, but server-side input rejection gives deterministic app behavior and easier tests.

### Treat Closing as Browser Detach Only

Closing a tmux tab closes the browser WebSocket and kills only the local `node-pty` attach process for that browser client. It must not run `tmux kill-session`, `houmao-mgr agents stop`, AG-UI detach, interrupt, restart, or registry cleanup.

Alternative considered: detach all tmux clients for the session on close. That can disrupt external terminal users and other browser tabs. The bridge should clean up only the client process it created.

### Persist Config, Not Terminal Bytes

Persist pane layout and non-sensitive tmux config in the existing localStorage workbench storage. Do not persist xterm scrollback, terminal input, raw output, or WebSocket payloads in localStorage or IndexedDB. On reload, a restored tmux tab may reconnect to the selected session, but its visible scrollback starts from the new attach stream.

Alternative considered: persist scrollback for convenience. That stores raw terminal content, which can include credentials, prompts, mailbox content, memory content, and proprietary source snippets. The workbench persistence boundary already forbids raw terminal content.

## Risks / Trade-offs

- Native dependency friction with `node-pty` → Keep the dependency scoped to `apps/ag-ui-workbench`, document local prerequisites, and make tmux bridge unavailability a visible status instead of an app crash.
- WebSocket routing conflict with Vite HMR → Use a dedicated `__houmao_tmux` prefix and only handle matching upgrade requests.
- Passive server unavailable during Houmao-only filtering → Show raw sessions when the checkbox is off and a clear no-Houmao-matches state when it is on.
- Read-only bypass attempts through crafted WebSocket messages → Enforce read-only in the host bridge, not only in the browser terminal.
- Terminal output leaks through persistence → Keep terminal buffers in memory only and add tests that inspect localStorage for absence of terminal content.
- Closing a tab accidentally controls an agent → Keep tmux close logic limited to the spawned attach process and add tests that no lifecycle or AG-UI detach route is called.
- Operator marker mistakenly treated as protocol state → Keep the marker out of AG-UI request bodies and add tests that operator-marked panes submit the same minimal requests as ordinary agent panes.
- Background watcher steals the default AG-UI publish target → Update last-bound-thread only from explicit foreground/viewed pane transitions, not every `/connect` stream.
- Stale last-sent-thread routes to a thread with no live GUI → Preserve live-only delivery counts so the response reports zero delivery, and do not make the gateway replay missed GUI events.
- Agent publishes from tmux before any destination state exists → Send to the default sink, log safe routing metadata, return a default-sink warning, and teach the system skill not to claim GUI visibility.

## Migration Plan

Existing workbench localStorage records may include an `operator` pane and do not include `tmux` panes. The storage sanitizer should stop recreating the `operator` pane by default, clear invalid operator markers, and add `tmux` handling only for valid new records. No durable migration is required for existing users.

Gateway last-bound-thread and last-sent-thread state is process-local and starts empty after restart. The workbench will set last-bound-thread again when the user views or reconnects an agent pane. The gateway will refresh last-sent-thread after later publishes to concrete thread destinations. No persisted migration is required.

If rollback is needed, removing the `tmux` plugin and pane kind should leave ordinary AG-UI panes intact. Persisted `tmux` pane records from a newer version may be ignored by the older sanitizer.

## Open Questions

- Should the tmux picker remember the last Houmao-only filter choice globally, or only per tmux tab?
- Should restored tmux tabs auto-reconnect on page reload, or wait for an explicit Attach click? The safer default is explicit attach because it avoids surprising terminal connections after reload.
