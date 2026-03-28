## Context

`houmao-mgr agents gateway prompt` currently rides the queued gateway request surface end to end. The CLI calls the managed-agent gateway request path, the live gateway accepts `submit_prompt` onto `/v1/requests`, and the caller gets a `GatewayAcceptedRequestV1` response with `request_id` and `queue_depth` before the runtime knows whether the prompt was actually dispatched to the agent surface.

That contract works for durable queued work, but it does not satisfy the operator semantics requested here:

- only send the prompt when the underlying agent is actually ready by default
- allow an explicit `--force` override
- print JSON describing whether the prompt was really sent
- exit non-zero when prompt delivery is refused

The existing gateway availability signals are too coarse for that job. For local TUI targets, `request_admission=open` is currently derived from connectivity and recovery state, not from prompt-ready TUI posture. Meanwhile the repo already has richer gateway-owned TUI state that exposes `turn.phase`, `surface.accepting_input`, `surface.editing_input`, `surface.ready_posture`, `stability`, and parsed-surface fields such as `business_state` and `input_mode`. For native headless sessions, the system already models "can accept prompt now" as "runtime operable and no active execution". `send-keys` is already a separate immediate control route and should stay that way.

This change crosses the gateway runtime, CLI, pair-server proxy routes, passive-server proxy routes, docs, and tests, so a design artifact is warranted.

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr agents gateway prompt` an honest ready-or-refuse control path instead of a queue-acceptance shortcut.
- Preserve the existing raw `send-keys` behavior as immediate exact control input rather than turning it into another prompt-like API.
- Reuse existing gateway-owned TUI tracking state and headless execution state instead of adding provider-specific prompt heuristics from scratch.
- Keep the transport-neutral `houmao-mgr agents prompt ...` contract unchanged.
- Keep a clear separation between queued gateway work and immediate live prompt control.
- Fail explicitly for unsupported backends such as `codex_app_server` instead of guessing.

**Non-Goals:**

- Remove the existing queued gateway request surface from the protocol in this change.
- Redesign interrupt behavior or gateway mail-notifier behavior.
- Add support for `codex_app_server` direct gateway prompt control.
- Redefine global `request_admission` semantics for every existing gateway consumer.
- Turn the gateway prompt path into a durable per-request history API.

## Decisions

### 1. Add a new immediate prompt-control route instead of repurposing the queued request route

The gateway will keep `POST /v1/requests` for queued gateway request semantics. This change adds a separate immediate control route:

- direct gateway: `POST /v1/control/prompt`
- pair server proxy: `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- passive server proxy: `POST /houmao/agents/{agent_ref}/gateway/control/prompt`

The new route will accept a prompt body plus `force`, and it will return a direct prompt-control success payload only after the prompt has been admitted for live dispatch on the current backend.

Why this over repurposing `POST /v1/requests`:

- `POST /v1/requests` already means "accepted onto the queue", and its response model is built around that meaning.
- Reusing that route would preserve the same ambiguity the user wants to remove.
- Keeping both surfaces lets existing queued flows survive while giving the CLI one truthful "sent now or refused now" control path.

### 2. `houmao-mgr agents gateway prompt` switches to direct control and owns structured JSON error output

The CLI command will stop calling the gateway request proxy for prompts and will call the new direct prompt-control route instead. Success output stays JSON through the normal command output path. Refusals will not rely on generic Click text formatting; the command will emit a structured JSON error payload and exit non-zero.

The prompt-control request body will carry:

- `prompt`
- `force` (default `false`)

The success payload will carry enough information for operator scripts to tell that the prompt was dispatched, for example:

- `status`
- `action`
- `sent`
- `forced`
- `detail`

Why this over preserving generic CLI error handling:

- The user explicitly wants JSON on the console for this command, including the refusal case.
- A targeted helper for this command is lower risk than redefining every `houmao-mgr` failure path globally.

### 3. Prompt readiness is evaluated per route from gateway-owned live state; `request_admission` stays coarse

This change will not redefine `GatewayStatusV1.request_admission` into a universal prompt-readiness flag. Existing code already uses that field as a coarse gateway availability/recovery signal, and changing its meaning would create wider behavioral fallout.

Instead, the new prompt-control route will evaluate readiness directly:

- For TUI-backed sessions, read gateway-owned TUI state and require:
  - `turn.phase = "ready"`
  - `surface.accepting_input = "yes"`
  - `surface.editing_input = "no"`
  - `surface.ready_posture = "yes"`
  - `stability.stable = true`
  - when `parsed_surface` is available, additionally require `business_state = "idle"` and `input_mode = "freeform"`
- For native headless sessions, require:
  - runtime control is operable
  - no active execution
  - no active turn already in flight

If readiness cannot be established confidently, the route will reject unless `force=true`.

Why this over gating only on `request_admission` or `terminal_surface_eligibility`:

- The existing status snapshot is too coarse for TUI prompt-safety decisions.
- The gateway-owned tracked TUI surface already exposes the exact fields the operator semantics need.
- This keeps the new behavior local to prompt control instead of redefining older status consumers in the same change.

### 4. `--force` bypasses only prompt-readiness checks

`force=true` allows prompt control to proceed when the target is connected but not judged prompt-ready. It does not bypass:

- missing or blank prompt validation
- unavailable or detached gateway state
- reconciliation-blocked gateway state
- unsupported backend errors

Why this over a broader "ignore everything" force flag:

- The operator request is about overriding busy/not-ready posture, not overriding fundamental safety or topology failures.
- A narrow force contract is easier to reason about and document.

### 5. Backend execution stays semantic for prompts and direct for raw control input

Prompt control will continue using semantic prompt submission under the addressed backend instead of rewriting prompts into literal `send-keys` text bursts.

Implementation posture by backend:

- `local_interactive`: execute semantic prompt submission after readiness gating
- native tmux-backed headless backends: admit only when idle, then start prompt work immediately without requiring the caller to wait for the whole turn to finish before receiving a success response
- `codex_app_server`: reject as unsupported for now

Raw `send-keys` remains a distinct immediate control-input route. It will not consult prompt-readiness or "busy" posture before forwarding the exact control input, though it will still reject ordinary unavailability or reconciliation failures.

Why this over making `send-keys` share the prompt gate:

- The user explicitly wants `send-keys` to behave as direct operator control even when the agent is busy.
- Raw control input is for exact manipulation, not semantic prompt safety.

## Risks / Trade-offs

- [Two prompt surfaces may confuse operators] → Keep `agents prompt` as the default documented path, document `agents gateway prompt` as the explicit live-control path, and explain that queued gateway requests remain a separate lower-level surface.
- [Headless success means "started" rather than "completed"] → Make the success payload describe prompt dispatch/admission only, not turn completion.
- [TUI readiness may be conservative when tracker state is ambiguous] → Reject by default and provide `--force` for operators who intentionally want to push through.
- [Structured JSON failure output is different from generic CLI failures] → Scope that behavior to `agents gateway prompt` instead of changing every `houmao-mgr` command.
- [Unsupported backend coverage may surprise callers] → Reject explicitly with a clear not-implemented message for `codex_app_server` rather than silently pretending the gateway can reason about readiness there.

## Migration Plan

1. Add prompt-control request/result models plus direct gateway, pair-server, and passive-server route support.
2. Implement prompt-control readiness evaluation for TUI and native headless gateways while leaving queued request handling intact.
3. Switch `houmao-mgr agents gateway prompt` to the new route, add `--force`, and add structured JSON failure emission.
4. Update gateway docs, CLI docs, and workflow docs to stop promising `request_id`/`queue_depth` for this command.
5. Expand tests to cover ready dispatch, refusal, forced dispatch, raw `send-keys` during busy posture, and explicit unsupported-backend behavior.

Rollback is straightforward because the older queued request route remains present. Reverting the CLI to the queued route restores the old contract without requiring storage or schema rollback.

## Open Questions

- Should the repo later expose the queued gateway prompt surface as an explicit advanced CLI command such as `agents gateway enqueue-prompt`, or leave it as an internal/API-only surface?
- Should gateway status eventually gain a first-class TUI `can_accept_prompt_now` field so operators can read prompt readiness directly from `/v1/status` instead of inferring it from the tracked TUI state route?
