## Why

The current headless chat-session idea is ambiguous. A caller can mean "continue the managed agent's current conversation", "ask the tool for its latest stored chat", "start fresh", or "use this exact provider session id", but a single overloaded `last`-style selector cannot represent those meanings cleanly.

## What Changes

- Replace the overloaded headless prompt selector with a structured `chat_session` object for immediate prompt control and managed headless turn submission.
- Define explicit headless session concepts in the public contract: `current`, `startup_default`, `tool_last_or_new`, `exact`, and `auto`.
- Make omitted headless chat-session selection equivalent to `auto`, so callers get predictable common-sense behavior without needing to understand the full state machine.
- Expose headless control-state fields that distinguish the managed agent's pinned current session, its startup default selector, and any pending one-shot next-prompt override.
- Add a dedicated headless-only `POST /v1/control/headless/next-prompt-session` route, plus matching pair-owned proxy routes, for a one-shot "next auto prompt starts fresh" override.
- Allow TUI-backed prompt control to accept only `chat_session.mode = new`, implemented as a clear-then-send workflow, and reject every other explicit chat-session mode with validation semantics.
- Carry the same structured selector semantics through the Houmao-owned managed headless turn path so direct server-backed headless prompting and gateway-backed headless prompting resolve chat-session choice the same way.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-gateway`: extend live gateway prompt-control and headless control-state behavior to use an explicit structured chat-session selector model with auto resolution, one-shot next-prompt override, and TUI support for `mode = new`.
- `houmao-server-agent-api`: extend managed headless turn submission and managed-agent gateway control routes so server-backed callers can use the same structured headless chat-session semantics.
- `passive-server-gateway-proxy`: extend gateway proxy routes to forward the structured headless chat-session selector and the one-shot next-prompt-session control routes.

## Impact

- Gateway HTTP models, client methods, state payloads, and prompt-dispatch logic under `src/houmao/agents/realm_controller/`
- Pair-owned server HTTP models, routes, and gateway/headless submission services under `src/houmao/server/`
- Managed headless turn admission paths and persistence of normalized selector intent for gateway-backed and direct server-backed headless work
- Gateway and server tests for auto resolution, `current` versus `tool_last_or_new` semantics, TUI `mode = new` clear-then-send behavior, unsupported TUI mode rejection, one-shot next-prompt override behavior, and proxy forwarding
- Gateway and server API reference docs for the new structured selector contract and headless control-state fields
