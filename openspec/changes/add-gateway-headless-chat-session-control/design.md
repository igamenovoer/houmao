## Context

The problem is not just missing functionality; it is ambiguous vocabulary. In headless mode there are at least four distinct concepts:

- a fresh chat with no prior context,
- the concrete provider session currently pinned by this managed agent,
- the underlying tool's own notion of "latest stored chat",
- one exact provider session id supplied by the caller.

The earlier draft overloaded those meanings into a string field that mixed ids and selector keywords. That makes both user intent and implementation precedence hard to reason about.

The clearer model is to separate:

- `current`: an exact provider session id currently pinned by the managed agent after a successful turn,
- `startup_default`: how the managed agent should choose its first chat when no `current` exists,
- `tool_last_or_new`: a selector that asks the tool to resume its latest stored chat and falls back to fresh if none exists,
- `new`: a fresh chat,
- `exact`: an exact provider session id,
- `auto`: common-sense default selection based on the managed agent's current state.

The repository already has the right implementation anchors for this:

- headless runtimes persist the concrete provider `session_id`,
- headless launches and joins already persist an initial resume-selection concept,
- the live gateway already distinguishes TUI and headless control paths,
- pair-owned managed-agent APIs already proxy direct gateway control routes and already expose a dedicated managed headless `/turns` route family.

## Goals / Non-Goals

**Goals:**
- Make headless chat-session selection unambiguous for users and implementers.
- Give callers a structured selector contract instead of a mixed keyword-or-id string.
- Define `auto` so omitted selection behaves predictably in the common case.
- Expose enough state for callers to understand `current`, `startup_default`, and one-shot override posture.
- Support one explicit TUI reset case, `chat_session.mode = new`, while rejecting the rest of the chat-session selector model on TUI explicitly.
- Keep server-backed headless routing aligned with the same selector semantics.

**Non-Goals:**
- Changing queued gateway request submission (`POST /v1/requests`) in this change.
- Changing the transport-neutral managed-agent `/requests` route in this change.
- Persisting the one-shot next-prompt override across gateway restart.
- Adding history-browsing APIs for all tool-native sessions.
- Supporting an exact-session one-shot override route; exact targeting remains per-prompt.

## Decisions

### Decision: Replace the string selector with a structured `chat_session` object

The prompt-control and headless-turn request shape will use:

```json
{
  "chat_session": {
    "mode": "auto | new | current | tool_last_or_new | exact",
    "id": "required only for exact"
  }
}
```

For headless targets:

- `auto` means use the managed agent's default resolution behavior,
- `new` means force fresh provider-chat bootstrap,
- `current` means require the gateway/server to use its pinned current provider session,
- `tool_last_or_new` means ask the tool to resume its own latest stored chat and fall back to fresh if none exists,
- `exact` means use the provided provider session id exactly.

The `id` field is required when `mode = exact` and forbidden for all other modes.

For TUI prompt control:

- omitting `chat_session` keeps the existing ordinary prompt-control behavior,
- `chat_session.mode = new` is accepted,
- `chat_session.mode = auto | current | tool_last_or_new | exact` is rejected with validation semantics.

Why this approach:
- it stops pretending that every selector is a session id,
- it separates user intent from implementation detail,
- it gives room for explicit `auto` and `current` semantics without overloading `last`,
- it lets TUI expose one useful reset behavior without pretending TUI has headless-style provider session state.

Alternatives considered:
- keeping `chat_session_id` and documenting special string values.
  Rejected because the field name remains misleading and the distinction between `current` and tool-native latest stays muddy.

### Decision: Omitted selection means `auto`

For headless prompt control, omitting `chat_session` is defined as `chat_session.mode = auto`.

`auto` resolves in this order:

1. one-shot `next_prompt_override` if present,
2. `current` if present,
3. `startup_default`,
4. `new`.

This makes the common case predictable:

- continue the managed agent's active conversation when it already has one,
- otherwise honor the managed agent's configured startup behavior,
- otherwise start fresh.

Why this approach:
- it matches how users usually expect an ongoing managed agent to behave,
- it avoids forcing callers to choose between too many explicit modes for normal use,
- it keeps default behavior tied to managed-agent state rather than to an unrelated tool-global heuristic.

Alternatives considered:
- making omission mean `current`.
  Rejected because first-prompt behavior becomes undefined when `current` is absent.
- making omission mean `tool_last_or_new`.
  Rejected because a managed agent would silently jump to a tool-global latest chat even when the caller did not ask for that.

For TUI prompt control, omission does not become `auto`; it remains ordinary prompt submission with no explicit conversation-reset request. This keeps TUI behavior simple and makes explicit `chat_session.mode = new` the only transport-specific opt-in reset action.

### Decision: Expose explicit headless control-state concepts

`GET /v1/control/headless/state` will expose a structured headless chat-session state with at least:

- `chat_session.current`
- `chat_session.startup_default`
- `chat_session.next_prompt_override`

`chat_session.current` identifies the concrete provider session currently pinned by the managed agent, or `null` if none is pinned.

`chat_session.startup_default` identifies the managed agent's first-chat fallback behavior and uses only:

- `new`
- `tool_last_or_new`
- `exact`

`chat_session.next_prompt_override` is either `null` or a one-shot override object. In this change it only supports `mode = new`.

Why this approach:
- it gives users names for the three states they actually care about,
- it makes `current` visibly different from tool-native latest,
- it gives `auto` a transparent state model to read from.

Alternatives considered:
- exposing only one flat `current_chat_session_id` field.
  Rejected because it hides the managed agent's startup policy and pending override behavior.

### Decision: One-shot override uses a dedicated `next-prompt-session` route and only supports fresh chat

The live gateway will expose:

- `POST /v1/control/headless/next-prompt-session`

The pair-owned managed-agent gateway surface will expose matching proxy routes.

That route sets `chat_session.next_prompt_override = { "mode": "new" }`.

The override:

- is headless-only,
- is gateway-local live state rather than durable persisted state,
- is lost on gateway restart,
- is consumed only by the next accepted prompt whose effective selector is `auto` (either omitted or explicitly `auto`),
- is not consumed by prompts that explicitly request `new`, `current`, `tool_last_or_new`, or `exact`,
- does not affect queued requests, wakeups, mail-notifier behavior, or internal gateway-generated prompts.

Why this approach:
- it gives users a simple "fresh next prompt" control that does not distort the per-prompt selector model,
- it keeps one-shot mutable state narrow,
- it avoids pretending that a future exact session choice should live outside the prompt that uses it.

Alternatives considered:
- making the next-prompt route support `exact`.
  Rejected because exact session choice should stay local to the prompt that needs it.
- making the next-prompt route support `tool_last_or_new`.
  Rejected because that behavior is already available directly through per-prompt `chat_session.mode` and does not need mutable gateway state.

### Decision: TUI supports only `chat_session.mode = new` through a clear-then-send workflow

For TUI-backed prompt control, `chat_session.mode = new` means "reset the current chat context before submitting the actual prompt".

The gateway will realize that by:

1. confirming the TUI target is in a prompt-ready posture suitable for semantic prompt submission,
2. sending a semantic reset prompt such as `/clear`,
3. waiting until the tracked TUI state stabilizes back to a prompt-ready posture,
4. sending the caller's actual prompt.

If the target backend does not support the configured clear workflow, if the reset prompt cannot be admitted, or if the TUI does not stabilize back to prompt-ready posture within the allowed wait, the gateway fails the request explicitly and does not claim that the actual prompt was delivered.

This TUI `new` flow does not create or expose headless-style `current`, `startup_default`, or `next_prompt_override` state.

Why this approach:
- it matches the user's intuitive "start a new chat" expectation on TUI surfaces,
- it uses an operator-visible workflow that already exists in many TUI agents,
- it avoids fabricating unsupported TUI semantics for `current`, tool-native latest, or exact provider session ids.

Alternatives considered:
- rejecting all `chat_session` usage on TUI.
  Rejected because `new` maps naturally to an existing reset workflow and is useful enough to support directly.
- treating TUI `new` as an immediate blind `/clear` plus prompt injection without stabilization.
  Rejected because prompt delivery after reset needs a readiness check or the feature becomes race-prone.

### Decision: Successful prompt admission updates `current`

After a successful headless prompt turn, the resolved concrete provider session id becomes the managed agent's `current` session when the tool reports one.

That means:

- a successful `new` prompt pins its resulting new concrete session as `current`,
- a successful `exact` prompt pins that exact session as `current`,
- a successful `tool_last_or_new` prompt pins whichever concrete session the tool actually resumed or created,
- `auto` inherits whichever concrete session resulted from its resolved mode.

Why this approach:
- it keeps `current` meaningful as the managed agent's active conversation anchor,
- it lets `tool_last_or_new` act as a selector rather than pretending it is a stable gateway-owned session identity.

Alternatives considered:
- treating `tool_last_or_new` as a virtual state without updating `current`.
  Rejected because the managed agent would keep rediscovering the tool's latest chat instead of converging on one explicit active conversation.

### Decision: `current` is explicit and failure-visible

`chat_session.mode = current` means "use the managed agent's currently pinned session". If no `current` session exists, the request fails explicitly with conflict-style semantics rather than silently falling back.

Why this approach:
- it makes `current` a precise operator tool,
- it preserves the difference between "continue exactly this managed conversation" and "pick a sensible default".

Alternatives considered:
- making `current` fall back to `auto`.
  Rejected because that hides state mistakes and weakens the value of an explicit mode.

### Decision: Server-backed headless prompting uses the same selector model

The Houmao-owned managed headless turn route, `POST /houmao/agents/{agent_ref}/turns`, will accept the same `chat_session` object. When a live gateway is attached, the server will preserve that selector through gateway-backed admission. When no eligible gateway is attached, the server will apply the same selector semantics through its direct fallback headless path.

The pair-owned route `POST /houmao/agents/{agent_ref}/gateway/control/prompt` also uses the same selector model.

Why this approach:
- it keeps headless prompting semantically aligned across direct gateway and server-owned routes,
- it avoids two divergent definitions of `auto`, `current`, and `tool_last_or_new`.

## Risks / Trade-offs

- [The structured selector is more verbose than a single string] → Use omission-as-`auto` for headless common cases and keep TUI support narrowed to one explicit mode.
- [Users may still confuse `current` with tool-native latest] → Document the distinction explicitly and expose both `current` and `startup_default` in headless state.
- [One-shot override is live-only and can disappear on restart] → Keep it inspectable in headless state and scope it narrowly to the next `auto` prompt.
- [Different tools may report session ids differently] → Normalize tool-specific outputs into the shared `current` concept and fail explicitly when a required exact/current resolution cannot be satisfied.
- [TUI reset workflows are backend-specific and can be brittle] → Restrict TUI support to `mode = new`, require a configured clear workflow plus post-clear stabilization, and fail explicitly when the reset cannot be verified.
- [Changing the request contract is a clean break] → Accept the break intentionally; this change explicitly does not preserve compatibility with the earlier string-based idea.

## Migration Plan

1. Add structured `chat_session` request models and shared selector normalization helpers for gateway and server paths.
2. Extend gateway headless control-state models and routes to expose `current`, `startup_default`, and `next_prompt_override`.
3. Implement `auto` resolution, explicit mode handling, and current-session pinning in direct gateway headless prompt control.
4. Add the one-shot `POST /v1/control/headless/next-prompt-session` route and matching pair-owned proxy routes.
5. Extend managed headless turn submission and pair-owned prompt-control proxying to preserve the same selector model across gateway-backed and direct fallback execution.
6. Add tests for `auto`, `current`, `tool_last_or_new`, `exact`, one-shot override consumption, restart-loss behavior, TUI `mode = new` clear-then-send behavior, and unsupported TUI mode rejection.
7. Update gateway and server docs to explain the explicit state model and `auto` semantics.

Rollback removes the new structured selector and headless next-prompt route and restores the earlier simpler control surface if needed.

## Open Questions

- None. The design now distinguishes state (`current`, `startup_default`) from selectors (`auto`, `new`, `current`, `tool_last_or_new`, `exact`) and keeps the one-shot override intentionally narrow.
