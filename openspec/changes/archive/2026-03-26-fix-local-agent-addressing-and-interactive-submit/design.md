## Context

Serverless `houmao-mgr agents launch` already publishes enough metadata to distinguish managed-agent identity from the actual tmux session handle, but post-launch UX still leaks that internal split. Under the intended contract, `agent_id` is the globally unique authoritative identity and is what the system should use for registry layout, internal lookup, and unambiguous control. `agent_name` is required, user-facing, and intentionally not unique by design; it is only safe for control when exactly one live record currently uses that name. Tmux session names are separate runtime handles.

Today the CLI still centers one positional managed-agent reference, which blurs those responsibilities and encourages callers to treat friendly names as though they were always unique. The registry spec also still carries older language that implies global name uniqueness or canonical-name ownership rules that no longer match the intended contract. This change makes the identity layers explicit:

- `agent_id`: globally unique internal identity
- `agent_name`: non-unique friendly label
- `tmux_session_name`: runtime handle only

The second problem is lower-level. `LocalInteractiveSession.send_prompt()` currently reuses the raw tmux control-input path by sending literal text with `escape_special_keys=True` and then appending `Enter`. For Codex, that delivery pattern can be reclassified by the TUI as a non-bracketed paste burst, so the final `Enter` becomes a newline instead of a submit. The repo already has two important pieces we should reuse rather than bypass:

- the exact `<[key-name]>` control-input contract in `runtime-tmux-control-input`
- tmux buffer pasting with bracketed-paste support (`paste-buffer -p`) already used in compatibility code

This change cuts across local registry discovery, launch UX, runtime prompt delivery, and gateway execution, so a design artifact is warranted.

## Goals / Non-Goals

**Goals:**

- Keep authoritative managed-agent identity centered on globally unique `agent_id`, with `agent_name` as non-unique friendly metadata.
- Require `agent_id` and `agent_name` to remain safe as filesystem path components and URL path segments.
- Reshape `houmao-mgr agents ...` targeting around explicit `--agent-id` and `--agent-name` selectors, so ambiguity handling is deliberate instead of hidden inside one positional ref.
- Let serverless local `houmao-mgr agents ...` commands accept a tmux session name as a convenience alias when it resolves uniquely through shared-registry metadata.
- Make launch output tell operators exactly which `agent_id`, `agent_name`, and tmux session name were chosen.
- Split semantic prompt submission from raw key/control-input delivery at both runtime and gateway layers.
- Make local-interactive prompt submission reliable for Codex and similar TUIs by using a paste-aware delivery path instead of a fast literal keystream.

**Non-Goals:**

- Redefine tmux session names as the canonical managed-agent identity.
- Make `agent_name` unique again or use it as the registry directory key.
- Replace the existing `<[key-name]>` contract for raw key delivery.
- Expand this change into a general new automation DSL for provider TUIs.
- Rework the bounded in-memory local TUI history behavior in `houmao-mgr agents state/show/history`.

## Decisions

### 1. `agent_id` is globally unique and authoritative; `agent_name` is friendly and non-unique

`agent_id` remains the authoritative identity in registry records, manifests, docs, and server-managed APIs. `agent_name` remains required as friendly metadata, but is not unique by design and must not be treated as the registry ownership key.

When callers omit `agent_id`, runtime publication derives it as `md5(agent_name).hexdigest()`. If callers need a different globally unique identity because they maintain external bookkeeping, they must provide `agent_id` explicitly. If they choose conflicting names and rely on the md5 fallback anyway, that is their responsibility by contract. We will not redefine `--session-name` as managed-agent identity.

Both `agent_id` and `agent_name` must be safe to embed in filesystem paths and URL path segments. That keeps registry layout, manifest references, and managed-agent HTTP routes from requiring extra escaping layers just to transport core identity fields.

For serverless direct control, `houmao-mgr` will extend local registry-first resolution to accept:

- exact `agent_id`
- unique `agent_name`
- unique exact `terminal.session_name` alias

This tmux alias remains intentionally limited to local registry-backed discovery. Server-managed resolution through pair APIs stays authoritative on the pair side and does not learn tmux-local aliases.

Why this over “make `agent_name` unique again”:

- It matches the intended contract: globally unique `agent_id`, friendly non-unique `agent_name`, separate runtime handle.
- It avoids overloading friendly labels with ownership semantics they are not supposed to carry.
- It still preserves an ergonomic path for friendly-name addressing when the registry can prove uniqueness at lookup time.

### 2. `houmao-mgr agents ...` targeting moves to explicit selectors instead of one positional managed-agent ref

Managed-agent CLI commands will stop centering one positional `<agent-ref>` for controlled actions. Instead, commands that target a managed agent should accept:

- `--agent-id <id>`
- `--agent-name <name>`

Exactly one of those selectors must be provided for explicit target selection.

Resolution behavior becomes:

- `--agent-id`: exact unique lookup only
- `--agent-name`: allowed only when exactly one fresh live record matches
- no selector: only valid for flows that already have a separate current-session contract

Why this over keeping one positional ref:

- It forces operators and automation to state whether they are choosing exact identity or friendly-name lookup.
- It prevents the CLI shape from implying that friendly names are always unique.
- It composes cleanly with the existing current-session attach exception in the gateway surface.

### 3. `houmao-mgr agents launch` must print both managed-agent identity fields and tmux identity explicitly

Launch output will become an explicit summary instead of the current `agent=<...> manifest=<...>` line. The output should surface:

- `agent_name`: the required user-facing managed-agent identity
- `agent_id`: the exact authoritative globally unique identity
- `tmux_session_name`: the actual tmux session handle
- `manifest_path`

This keeps the model understandable even if operators never read the registry files directly.

Why this over relying on `agents list` after launch:

- It removes a second discovery step from the common case.
- It makes the meaning of `--session-name` clear at the moment the operator chooses it.
- It makes the `agent_name` versus `agent_id` contract visible to operators immediately.

### 4. Semantic prompt submission and raw key delivery become separate runtime operations

`LocalInteractiveSession` will keep a semantic `send_prompt()` operation and gain or formalize a distinct raw control-input operation for exact `<[key-name]>` sequences. The semantic path is for “submit this message to the provider.” The raw path is for “inject these literal characters and/or exact keys into the live TUI.”

The raw path continues to use the `runtime-tmux-control-input` contract:

- exact `<[key-name]>` tokens
- case-sensitive key names
- no implicit Enter
- optional full-string literal escaping

The semantic prompt path has the opposite public contract:

- treat the entire prompt body as literal text
- do not parse `<[key-name]>` substrings as special keys
- auto-submit once at the end

The semantic prompt path must not expose raw key-token parsing behavior to callers, even if the internal implementation uses tmux primitives to realize the final submit.

Why this over leaving one overloaded input primitive:

- Prompt submission carries stronger semantics than raw key injection and is what TUI tracking, gateway tracking, and operator workflows care about.
- The Codex failure came from conflating the two layers.

### 5. Local-interactive prompt submission uses bracketed-paste-aware tmux insertion plus separate submit

For semantic prompt submission into tmux-backed local-interactive sessions, the runtime will switch from `send-keys -l <text>` to tmux buffer paste with `paste-buffer -p`, then issue submit as a separate step.

The expected flow is:

1. load prompt text into a temporary tmux buffer
2. paste the buffer into the target pane with `paste-buffer -p`
3. wait a bounded post-paste interval suitable for provider input processing
4. send the explicit submit key separately

`paste-buffer -p` matters because tmux will emit bracketed-paste wrappers when the application requested bracketed paste mode. That lets Codex treat the injected text as paste input instead of a synthetic burst of typed characters.

Why this over “just sleep between literal characters and Enter”:

- It aligns with provider semantics instead of trying to guess timing well enough to dodge them.
- The repo already uses `paste-buffer -p` in other tmux automation code.
- Timing-only fixes are fragile across machines and providers.

### 6. Gateway prompt and gateway send-keys become separate control surfaces

The gateway will continue to use `POST /v1/requests` for queued semantic prompt submission (`submit_prompt`) and interrupts. It will add a separate explicit raw control-input route for `<[key-name]>` sequences, implemented through a distinct adapter method and runtime method.

The split is:

- semantic prompt: durable queue semantics, gateway request lifecycle, prompt-tracking hooks
- raw send-keys: explicit control route, `<[key-name]>` parsing, no implicit Enter, no prompt-tracking hook, no durable queued prompt semantics

This preserves the existing request model while making raw TUI driving available without lying that it is prompt submission.

Why this over adding `send_keys` as another queued request kind:

- Raw keys are operational control, not durable agent work.
- Reusing the queued prompt path would blur semantics again and would pollute TUI prompt tracking.

## Risks / Trade-offs

- [Friendly-name lookup becomes more visibly inconvenient] → That is intentional. Exact `agent_id` targeting remains available for automation, while `--agent-name` remains ergonomic for human use when the registry can prove uniqueness.
- [Identifier-format validation may reject legacy names] → Fail early and document the allowed format; this is preferable to silently carrying path-hostile or URL-hostile identifiers deeper into registry and HTTP code paths.
- [Local alias ambiguity] → Matching by `terminal.session_name` can become ambiguous if multiple fresh records reuse the same session name. Fail closed with an explicit ambiguity error listing `agent_id`, `agent_name`, and `terminal.session_name` for each candidate.
- [Prompt delivery still depends on provider readiness] → Bracketed paste fixes the Codex burst issue but does not guarantee that a provider is currently in a submit-ready composer state. Keep readiness checks and explicit error reporting unchanged.
- [New gateway control route may invite misuse] → Document that raw send-keys is an operator/debugging control path and does not create managed prompt history or turn semantics.
- [Implementation split touches multiple layers] → Keep the interface boundary tight: runtime semantic prompt method, runtime raw send-keys method, gateway adapter method for each, and thin CLI wiring.

## Migration Plan

1. Update identity validation and registry specs so `agent_id` is globally unique, `agent_name` is non-unique, and both remain path-safe and URL-safe.
2. Reshape `houmao-mgr agents` command targeting to use `--agent-id` and `--agent-name` selectors with explicit ambiguity handling.
3. Extend local registry resolution to recognize unique tmux session aliases and improve ambiguity errors.
4. Update `houmao-mgr agents launch` output to print the managed-agent identity summary explicitly.
5. Introduce separate runtime methods for semantic prompt submission and raw control-input delivery.
6. Switch local-interactive prompt submission to tmux buffer paste with bracketed-paste support plus explicit submit.
7. Add the gateway raw send-keys control route and wire gateway prompt execution to the semantic prompt path only.
8. Update workflow docs and tests for the serverless launch-plus-gateway flow.

Rollback is straightforward because the prompt-delivery change stays behind the existing semantic `send_prompt()` interface. The CLI-targeting reshape is more visible, but the implementation can preserve an internal transitional adapter if needed while still converging the public interface on explicit selectors.

## Open Questions

- Whether `houmao-mgr` should expose a first-class `agents gateway send-keys` command in the same change or leave the new gateway raw control route as an HTTP/testing surface first.
- Whether the post-paste submit path should use a fixed bounded delay for all providers or a provider-specific readiness wait hook for Codex only.
