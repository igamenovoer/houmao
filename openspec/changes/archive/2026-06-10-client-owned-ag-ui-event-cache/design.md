## Context

Houmao currently has two different AG-UI delivery needs. The gateway needs to expose standard AG-UI streams and accept standard AG-UI event batches from agents. The GUI needs to keep graphics visible across pane close, browser reload, and reconnect workflows when the user has expressed interest in a target.

Gateway-side retained replay mixes those needs. A publish can report that no GUI received an event live, but a later GUI reconnect may still display it from gateway storage. That behavior makes `delivered_count` hard for agents to interpret and turns the gateway into a partial event store.

The intended model is live transport plus client-owned observation. The gateway fans out accepted standard AG-UI events to matching streams that are connected now. The workbench decides which agent/thread targets it watches, keeps those streams open in the background, and stores the events it actually receives.

## Goals / Non-Goals

**Goals:**

- Make Houmao gateway AG-UI event ingestion live-only and send-and-forget.
- Make `delivered_count` mean live stream deliveries at publish time, with `stored_count = 0` for Houmao gateway publish.
- Let the workbench retain charts, dashboards, and raw AG-UI events it received even after a pane is closed and reopened.
- Let users watch an interested agent/thread without keeping a visible presentation pane open.
- Make missed events explicit: if the GUI was not watching, the gateway does not recover them later.

**Non-Goals:**

- Do not add durable server-side AG-UI event storage.
- Do not require the gateway to find, wake, or reconnect to GUI browsers.
- Do not make `houmao-mgr` a generic third-party AG-UI endpoint client.
- Do not promise cross-browser or cross-device GUI history sync.
- Do not change AG-UI core event shapes or embed Houmao cache cursors inside AG-UI event payloads.

## Decisions

### Gateway publish is live-only

The gateway will validate each submitted AG-UI event batch, broadcast accepted events to matching active connect or run streams, and return counts. It will not write accepted published events to a retained replay log. For Houmao gateway publish, `stored_count` will always be `0`, `replay` metadata will be absent or `none`, and `delivered_count` will count only live stream writes.

Alternative considered: keep a bounded gateway replay log but make the GUI prefer its local cache. That still leaves ambiguous publish results and creates two caches with different retention and loss behavior. Live-only gateway semantics give agents a clearer contract.

### Connect streams do not use replay cursors

`POST /v1/ag-ui/connect` can tolerate an old `lastSeenEventId` field for request compatibility, but the gateway will not treat it as a replay cursor for published GUI events. A new stream emits the current safe state snapshot and then future live events.

Alternative considered: reject `lastSeenEventId` after removing replay. Ignoring it is less brittle for clients during the transition, while capabilities make clear that replay is unsupported.

### The workbench owns watched-target state

The workbench will maintain a watched-target registry separate from Dockview panes. A watched target is keyed by its durable address: discovered targets use `agent_id` when available, otherwise an unambiguous `agent_name`; manual targets use the normalized AG-UI URL plus thread id. A watcher owns the active connect stream for that target/thread. Visible panes subscribe to watched-target state rather than owning the only stream.

Alternative considered: keep streams pane-local and persist only pane state. That fails the requirement that the GUI can listen to interested agents while not presenting graphics.

### The client cache stores received stream events

The workbench will store received standard AG-UI events in a browser-owned cache, preferably IndexedDB. The cache stores target key, thread id, local sequence, receive timestamp, optional SSE frame id, and the raw AG-UI event object. LocalStorage remains limited to layout, passive-server URL, pane target metadata, and watched-target metadata.

Alternative considered: use localStorage for event history. AG-UI graphics can be large, and localStorage is synchronous and small. IndexedDB fits append-heavy event history and bounded retention better.

### Panes are presentation, not subscription ownership

Closing a pane removes that presentation surface. It does not stop a watcher if the target remains watched. Unwatch or explicit disconnect stops the watcher; any gateway events published while no watcher is connected are lost for that GUI.

Alternative considered: make pane close always disconnect. That reproduces the current loss behavior and makes background listening impossible.

### Rendering reads from cache plus live updates

When a pane opens for a watched target, it loads cached events, reduces them into visible AG-UI state, and subscribes to new watcher events. The same renderer registry handles cached and live events, including Houmao typed components and unknown component fallbacks.

Alternative considered: persist reduced React state only. Raw event persistence is more testable, supports future reducer fixes, and keeps debugging evidence available.

## Risks / Trade-offs

- Browser cache can contain sensitive stream payloads -> the workbench must keep this explicit, avoid credentials and request bodies, provide bounded retention, and offer a clear cache-clear path.
- Local cache is browser-local -> another browser or device will not recover events that this browser did not receive.
- Watchers consume gateway connections in the background -> the UI must expose watched state and make unwatch/disconnect cheap.
- A gateway outage still loses events published during downtime -> reconnect resumes live delivery only; there is no server replay gap fill.
- Existing tests that expect replay will fail -> update fixtures and assertions to verify live-only loss and client-side retention.

## Migration Plan

1. Change gateway capabilities, connect, and publish behavior to stop advertising or using retained replay for published GUI events.
2. Remove or bypass gateway replay writes and replay reads for `/v1/ag-ui/events`.
3. Add the workbench watched-target registry and IndexedDB event cache behind the existing AG-UI reducer and renderer.
4. Move pane connection ownership into the watcher manager and update pane close, unwatch, and disconnect controls.
5. Update skills and docs so agents interpret `stored_count = 0` as normal for Houmao gateway publish.
6. Update deterministic gateway and Playwright tests around the new live-only and client-cache behavior.

Rollback is straightforward for frontend-only cache changes by disabling background watchers and using pane-local streams again. Rolling back gateway live-only behavior would reintroduce replay storage and requires restoring the previous capability and publish response semantics.

## Open Questions

- What exact default retention limit should the client cache use per watched target: event count, byte size, time window, or a combination?
- Should the initial implementation expose cache clearing globally only, or also per watched target?
- Should debug-agent relay events follow the same live-only semantics immediately, or keep a separate opt-in replay mode for lab-only tests?
