## Context

The AG-UI workbench reduces received AG-UI events into pane display state. Agent panes can show two state sources at once: a watched target runtime/cache stream and pane-local run stream events. The watched target runtime owns the browser event cache and background connect stream, while the visible pane owns local prompt-run output.

The current UI exposes a watched-target cache control in the watch strip, but that language is implementation-specific and does not cover pane-local output. The tester's intent is simpler: clear the graphics canvas and diagnostic evidence currently shown in the agent tab.

## Goals / Non-Goals

**Goals:**

- Provide a clear-canvas control on agent panes.
- Clear rendered graphics/tool calls, transcript messages, diagnostics, raw events, state snapshots, activity/custom events, and visible errors for the pane.
- For watched targets, clear the client event cache and in-memory reduced watched state so old graphics do not reappear after reconnect or pane reopen.
- Preserve active connect streams, reconnect loops, target metadata, prompt text, and agent/gateway lifecycle.
- Keep future AG-UI events rendering normally after a clear.

**Non-Goals:**

- Do not send a standard AG-UI event to request a remote reset.
- Do not clear agent memory, chat history, mailbox state, gateway queues, or gateway retained state.
- Do not stop, detach, restart, interrupt, or shut down a Houmao agent.
- Do not introduce gateway-side replay, cursor, or cache semantics.

## Decisions

### Use Client-Side State Reset

The clear-canvas action resets browser-owned reduced display state. It is not modeled as an AG-UI protocol message because the requirement is local presentation cleanup, not agent work.

Alternative considered: send a synthetic AG-UI command to the gateway or agent. That would couple a UI cleanup action to remote behavior and could accidentally alter agent execution, so the design rejects it.

### Clear Both Pane-Local and Watched-Target State

The handler SHALL always reset the pane-local `PaneEventState`. When the agent pane is presenting a watched target, it SHALL also invoke the watched-target clear path, which removes IndexedDB cached events for the target and resets the target runtime's reduced state.

This avoids the common failure mode where a visible chart disappears briefly and then reappears from the watched-target cache after reconnect or pane reopen.

### Keep Watcher Ownership Alive

For watched targets, clearing the canvas SHALL NOT unwatch the target or abort the active connect stream. The watcher keeps its connection, status, resolved target, and reconnect behavior. New events received after the clear are cached and rendered from an empty display baseline.

If multiple panes present the same watched target, the watched-target portion of clearing is target-owned. All panes presenting that target should lose the cached watched evidence together. Pane-local events remain local to the pane that was cleared.

### Present One User-Facing Action

The agent pane should expose one primary action named "Clear canvas", using an icon button in the pane header. The existing watched-strip cache control should either be removed or made secondary to the same clear-canvas behavior so testers do not need to distinguish "canvas" from "cache" during manual validation.

## Risks / Trade-offs

- Clearing a watched target affects all visible panes for that same watched target. This matches target-owned cache semantics, but it means the action is not strictly pane-private for watched output.
- IndexedDB clear can fail or be unavailable. The handler should surface a visible error while preserving the current connection and avoiding partial lifecycle side effects.
- Events already in flight can arrive immediately after clear. Those events should render normally; clear is a local reset point, not a stream barrier.

## Migration Plan

This is a browser UI behavior change only. No persisted schema migration is needed. Existing cached events remain valid until a user clicks Clear canvas or existing cache retention removes them.

## Open Questions

None.
