## Context

Houmao already has three pieces of the desired shape:

- The shared registry records authoritative `agent_id`, friendly `agent_name`, live generation, runtime pointers, and optional live gateway host/port.
- The passive server can list live discovered agents and resolve a live agent by id or name from its in-memory discovery index.
- The AG-UI workbench can select a discovered agent and connect to the selected per-agent gateway through `/v1/ag-ui`.

The weak part is the address boundary. Today the workbench stores and uses the resolved gateway URL as the practical target. That URL is a live transport detail. If the GUI starts first, the agent has no gateway yet. If the agent or gateway restarts, the old URL and `connectionId` become stale. If the GUI stream is absent when an agent publishes AG-UI graphics, current publish semantics can return `delivered_count = 0` and the GUI has no later recovery path.

The desired behavior is agent-addressed. A GUI pane targets a stable agent identity, preferably `agent_id` and optionally an unambiguous `agent_name`. The GUI actively resolves the current live gateway and reconnects when the agent or gateway changes. The gateway remains passive: it publishes live coordinates and serves requests, but it does not look for GUIs or maintain outbound GUI callbacks.

## Goals / Non-Goals

**Goals:**

- Make `agent_id` and unambiguous `agent_name` durable AG-UI workbench targets.
- Allow GUI-first, agent-first, gateway-restart, GUI-reload, and transient-network reconnect flows.
- Preserve direct manual AG-UI URL targeting for low-level tests and third-party endpoints.
- Make gateway-published AG-UI events recoverable after a GUI reconnect when bounded retention is available.
- Keep sensitive data out of registry records, passive-server responses, event logs, diagnostics, and browser storage.
- Preserve the lifecycle boundary: GUI connect/disconnect does not start, stop, interrupt, restart, or shut down the agent.

**Non-Goals:**

- The gateway will not initiate connections to browsers or search for GUI clients.
- This change will not make `agent_name` globally unique. Ambiguous names still require `agent_id`.
- This change will not guarantee unbounded historical replay. Replay is bounded by configured retention and falls back to snapshots.
- This change will not define third-party AG-UI endpoint delivery. Houmao publish helpers still publish only to Houmao gateways.
- This change will not require WebSocket. SSE remains the supported transport for this path.

## Decisions

### 1. GUI Owns Reconnect

The GUI pane runs a local connection state machine:

```text
┌────────────┐
│ resolving  │
└─────┬──────┘
      │ known but offline
      ▼
┌────────────┐      gateway appears      ┌────────────┐
│  waiting   │ ────────────────────────▶ │ connecting │
└────────────┘                           └─────┬──────┘
      ▲                                        │ stream open
      │ gateway lost                           ▼
┌─────┴──────┐                          ┌────────────┐
│ reconnect  │ ◀─────────────────────── │  attached  │
└────────────┘      stream error         └────────────┘
```

The gateway does not look for the GUI. This keeps the gateway simple, loopback-friendly, and consistent with existing HTTP/SSE behavior. It also handles GUI reloads naturally: a new browser instance starts from the saved agent address and resolves the current gateway.

Alternative considered: keep a passive-server relay stream open even while the agent is offline. That would hide gateway churn from the browser, but it makes the passive server responsible for long-lived stream multiplexing and retry policy. We should keep that as an optional proxy implementation detail, not the conceptual protocol.

### 2. Agent Address Is Stable, Gateway Coordinates Are Volatile

The saved target model should separate stable identity from live transport:

```json
{
  "source": {
    "kind": "discovered",
    "address": { "kind": "agent_id", "value": "abc123" },
    "agentId": "abc123",
    "agentName": "HOUMAO-test",
    "passiveServerUrl": "http://127.0.0.1:9891/"
  },
  "threadId": "abc123-thread"
}
```

The resolved gateway URL is cached only as the latest observation. The pane may display it for diagnostics, but it should not be the durable target when `source.kind = "discovered"`.

Alternative considered: keep persisting the direct gateway URL and refresh it opportunistically. That leaves ambiguity when the URL fails, because the GUI cannot tell whether the agent is offline, restarted, or replaced. Address-first storage gives a deterministic recovery path.

### 3. Passive Server Provides Address Resolution, Not GUI Callbacks

The passive server should expose a resolution response that can represent:

- unknown agent;
- ambiguous `agent_name`;
- known but offline agent;
- live agent without gateway;
- live agent with current gateway coordinates.

The response should include canonical `agent_id` when known. A name-based pane should adopt the resolved `agent_id` after a successful unique match while preserving the user's original name as display metadata.

This likely needs a known-agent view in addition to the current live-only discovery index. The existing `GET /houmao/agents` can remain a live list. A new or extended `GET /houmao/agents/{agent_ref}/resolve` can report offline-known state.

### 4. Reconnect Uses `lastSeenEventId`

Every replayable AG-UI SSE data frame should carry a durable event id. The AG-UI event payload stays standard; the event id is transport metadata:

```text
id: abc123:main-thread:42
data: {"type":"TOOL_CALL_START", ...}
```

The GUI records the highest contiguous applied event id per pane/thread. On reconnect it sends `lastSeenEventId` in `POST /v1/ag-ui/connect`. The gateway replays retained events after that cursor and then attaches the stream to live fanout. If the cursor is absent, too old, malformed, or from a different thread, the gateway emits a current `STATE_SNAPSHOT` and starts live streaming without claiming full replay.

This is at-least-once delivery. The GUI reducer must deduplicate by SSE event id where available and continue to tolerate duplicated AG-UI payloads.

### 5. Gateway Stores Before Fanout

For `/v1/ag-ui/events`, the gateway should validate the standard AG-UI batch, assign event IDs, append events to bounded per-thread storage, then fan out to active matching streams:

```text
POST /v1/ag-ui/events
      │
      ▼
validate AG-UI envelopes and sequence
      │
      ▼
append to per-thread event log
      │
      ▼
fan out to active subscribers
      │
      ▼
return accepted_count, stored_count, delivered_count
```

This changes how agents interpret `delivered_count = 0`: if `stored_count > 0`, the events were accepted for a future reconnect even though no live GUI stream received them immediately.

For run streams, durable event IDs should apply to gateway-published events merged into the stream. Native run observation events can initially remain snapshot/recomputed unless they are also added to the same log.

### 6. Capability Metadata Must Be Honest

The gateway should advertise `transport.resumable = true` and Houmao `replaySupport = "event_log_since_cursor"` only after durable replay is implemented for the route. Until then, clients should remain conservative.

The workbench should use capabilities when available, but its reconnect loop should not require replay support. Without replay support, reconnect still provides current state and future live events.

## Risks / Trade-offs

- Replay storage grows without bounds -> use per-thread event-count, byte-size, and age retention limits; expose retention metadata in capabilities or Houmao metadata.
- At-least-once replay duplicates UI records -> deduplicate by SSE event id and keep component renderers idempotent.
- Name-based targets can be ambiguous -> prefer `agent_id` after first unique resolution and surface `409 ambiguous` without guessing.
- Offline-known resolution may require a broader registry view than current live-agent discovery -> keep live list semantics unchanged and add a dedicated resolve surface for GUI reconnect.
- Gateway restart can lose event logs if storage is only in memory -> store replay logs under gateway-owned state paths, not process memory, when advertising resumable support.
- Sensitive payloads could enter event logs -> keep logs bounded and local, document their contents, avoid diagnostics that dump payloads, and preserve existing guidance against secrets in GUI payloads.
- Browser reconnect loops can overload passive server or gateway -> use exponential backoff with jitter and reset backoff on successful stream open.

## Migration Plan

1. Extend registry/passive-server resolution without changing the existing live list behavior.
2. Add gateway event IDs, bounded storage, publish response fields, and replay behavior behind honest capability metadata.
3. Update workbench target storage to preserve existing direct URL panes and introduce agent-addressed discovered panes.
4. Add active reconnect to discovered panes with conservative backoff and visible offline/reconnecting states.
5. Update `houmao-agent-ag-ui` guidance to explain `accepted_count`, `stored_count`, and `delivered_count`.
6. Keep manual direct URL behavior as the rollback path. If address-based resolution fails, users can still paste the current gateway URL.

## Open Questions

- Should the passive server expose the reconnect path only as resolution plus direct gateway URL, or also offer a browser-friendly proxy route that resolves by `agent_ref` before forwarding?
- What should the default event-log retention be for local development: count-based only, byte-based only, age-based, or a combination?
- Should run-observation events be persisted into the same event log now, or should the first milestone persist only externally published `/events` batches and rely on snapshots for run state?
