## Why

Gateway-owned AG-UI replay makes GUI graphics appear after a pane disconnects and reconnects, even when no GUI was listening at publish time. That blurs two different responsibilities: the gateway should provide live AG-UI transport, while the GUI should decide which agent streams it cares about and cache the events it actually received.

We want a simpler contract: gateway publishing is live fanout and send-and-forget. Missed GUI events are lost if no interested GUI listener is connected. To preserve graphics across pane close/reopen, the workbench must listen in the background for interested agents and store received AG-UI events on the client side.

## What Changes

- **BREAKING**: Houmao gateway AG-UI publish stops retaining published events for later replay. A publish reaches only currently connected matching AG-UI streams.
- Gateway AG-UI capabilities report non-resumable live delivery for published GUI events. `lastSeenEventId` is no longer a replay cursor for Houmao-published GUI events.
- The AG-UI workbench gains a client-owned event cache and watcher model. A watched agent/thread can keep a stream open even when no visible pane is rendering it.
- Workbench panes render graphics from the local client cache plus newly received live events. Closing a pane only closes presentation; unwatching/disconnecting stops the listener.
- Agent-facing skill and message-authoring guidance changes `delivered_count` and `stored_count` semantics so agents know that `stored_count=0` is expected and `delivered_count=0` means no live GUI listener received the message.

## Capabilities

### New Capabilities

- `ag-ui-workbench-client-event-cache`: Define browser-owned caching, watched-target lifecycle, pane rendering from cached events, and live-only loss semantics when the GUI is not listening.

### Modified Capabilities

- `per-agent-ag-ui-attachment`: Change gateway AG-UI publish from retained replay to live-only fanout, and update connect/capability response semantics.
- `ag-ui-workbench-app`: Integrate background watchers and cached event reduction into the workbench app lifecycle.
- `ag-ui-workbench-agent-picker`: Let users mark agents/threads as watched independently from opening or closing presentation panes.
- `houmao-agent-ag-ui-skill`: Teach agents that GUI event delivery is live-only unless a GUI watcher is connected and caching events client-side.
- `houmao-ag-ui-message-authoring`: Clarify that Houmao gateway publishing reports live acceptance and delivery only; third-party endpoints remain caller-managed.

## Impact

- Gateway runtime removes retained AG-UI publish replay behavior and updates publish/connect diagnostics.
- Workbench frontend adds a durable browser cache, background watcher state, watch/unwatch controls, and pane rendering from cached stream content.
- Agent skills and docs update delivery guidance so agents do not claim a graphic is visible when `delivered_count=0`.
- Tests need to cover live-only gateway delivery, client-side retention after pane close/reopen, and event loss after unwatch/disconnect.
