## Context

Houmao already has the right runtime shape for per-turn headless flexibility: native headless turns execute as a fresh CLI invocation per turn, and gateway prompt dispatch already distinguishes TUI, local headless, and server-managed headless control paths. At the same time, the public request contracts for managed headless turns and gateway prompt control currently expose prompt text and chat-session selection, but not request-scoped model or reasoning overrides.

Houmao also already has a normalized model-selection contract with a shared `name` field and normalized `reasoning.level` range `1..10`. That contract is currently centered on launch-owned configuration and tool-native startup projection. The missing piece is a supported request-scoped execution layer for headless prompt submission that reuses the same normalized shape without creating persistent live session state.

This change crosses four capability areas:

- unified model selection and reasoning normalization
- direct and queued gateway prompt submission
- managed-agent server prompt routes
- `houmao-mgr` prompt submission surfaces

## Goals / Non-Goals

**Goals:**

- Allow one headless prompt request to choose a different model or reasoning level than the agent's launch defaults.
- Reuse Houmao's normalized model-selection payload instead of inventing a gateway-only or CLI-only schema.
- Keep the override request-scoped and non-persistent.
- Support the same semantics across direct gateway prompt control, queued gateway prompt submission, managed headless turns, and the relevant `houmao-mgr` commands.
- Reject unsupported TUI combinations clearly instead of silently ignoring execution overrides.

**Non-Goals:**

- Persisting a live "current model" mutation for a running agent.
- Rewriting recipes, specialists, launch profiles, auth bundles, manifests, or runtime homes as durable state.
- Standardizing advanced vendor-native tuning beyond `model.name` and `reasoning.level`.
- Guaranteeing that a provider will accept reuse of an existing chat session when the model changes.
- Extending execution overrides to TUI-backed prompt flows.

## Decisions

### Decision: Add a request-scoped `execution.model` object as a sibling of `chat_session`

All supported headless prompt submission routes will accept:

```json
{
  "prompt": "...",
  "chat_session": { "mode": "current" },
  "execution": {
    "model": {
      "name": "gpt-5.4-mini",
      "reasoning": { "level": 4 }
    }
  }
}
```

`chat_session` and `execution` are intentionally orthogonal:

- `chat_session` selects conversation/session continuity
- `execution.model` selects model and reasoning for this submitted prompt

Alternative considered:
- Put model fields at the top level.
- Rejected because it makes the request harder to extend and mixes prompt content with execution control.

### Decision: Reuse the unified model-selection shape

`execution.model` will use the same normalized contract already used by launch-owned model selection:

- `name`
- `reasoning.level` in the inclusive range `1..10`

Partial overrides are valid:

- model only
- reasoning only

Missing subfields inherit from the agent's launch-resolved defaults for that turn.

Alternative considered:
- Add gateway-specific or tool-specific model and thinking fields.
- Rejected because it would duplicate normalization logic and fragment CLI and API behavior.

### Decision: Keep the override request-scoped and non-persistent

The override applies only to the accepted prompt submission being executed.

It does not update:

- launch profiles
- recipes
- specialists
- manifests
- gateway headless chat-session state
- durable turn metadata as historical "current model" state

The only tolerated temporary durability is existing queued gateway request storage, where the request payload may contain the override while waiting to run. That queue record is transport state, not a new live model-state store.

Alternative considered:
- Session-scoped live override persisted in runtime manifest.
- Rejected because it adds stateful behavior the user explicitly does not want and makes later turn behavior harder to reason about.

### Decision: Support the same override on both direct and queued gateway prompt surfaces

Both gateway prompt surfaces need the same capability:

- `POST /v1/control/prompt`
- `POST /v1/requests` with `kind = submit_prompt`

The same is true for server-owned managed-agent surfaces:

- `POST /houmao/agents/{agent_ref}/turns`
- `POST /houmao/agents/{agent_ref}/requests` with `submit_prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/requests` with `submit_prompt`

This avoids a split where one path can override model selection and another path silently cannot, even though both land on the same headless backend.

Alternative considered:
- Support overrides only on direct prompt control.
- Rejected because `houmao-mgr agents prompt` and managed headless `/turns` can route through queued or server-mediated submission paths.

### Decision: Extend the execution adapter and headless backend seam with an optional effective model override

Gateway adapters already abstract prompt dispatch. We will extend that seam to accept an optional resolved execution override for one prompt submission. Server direct-fallback headless execution will use the same underlying headless backend capability.

The backend rule is:

- prefer direct CLI flags or env when the tool supports them
- otherwise do temporary patch-and-restore of the Houmao-owned runtime config around that one subprocess invocation

We will not create a fresh temporary runtime home for every overridden turn by default. Headless sessions may rely on existing runtime-home state to resume provider chats correctly, so cloning the home risks breaking chat continuity.

Alternative considered:
- Per-turn cloned runtime home.
- Rejected because it is more expensive and can break session reuse semantics.

### Decision: Reject execution overrides for TUI-backed targets

For TUI-backed prompt paths, supplied `execution` is a validation error. Houmao must not silently ignore the field.

This applies to:

- direct gateway prompt control for TUI
- queued gateway `submit_prompt` for TUI
- transport-neutral managed-agent prompt submission when the resolved target is TUI
- `houmao-mgr agents prompt` and `houmao-mgr agents gateway prompt` after target resolution

Alternative considered:
- Ignore execution overrides on TUI targets.
- Rejected because silent downgrade would make automation unsafe and surprising.

## Risks / Trade-offs

- [Provider rejects model switch on reused chat session] → Preserve request-scoped semantics, surface the underlying dispatch failure clearly, and do not promise cross-model session continuity.
- [Per-turn patch-and-restore leaves stale config if a process crashes mid-turn] → Limit this to Houmao-owned headless homes, use `finally`-style restoration, and rely on existing single-active-turn-per-agent behavior to avoid concurrent mutations.
- [Behavior diverges across direct, queued, and server-mediated routes] → Use one shared request model and one shared execution-resolution helper across gateway and server code paths.
- [CLI becomes confusing if flags appear to work everywhere] → Resolve the target before dispatch and fail clearly on TUI-backed targets.
- [Tool-native support differs across Codex, Claude, and Gemini] → Keep the public contract normalized and let the backend projection layer own per-tool translation.

## Migration Plan

This is an additive API and CLI change.

1. Add request models and validators for `execution.model`.
2. Thread the new field through direct gateway prompt control, queued gateway `submit_prompt`, managed headless turn submission, and managed-agent prompt routes.
3. Extend gateway adapters and server direct-fallback headless execution to accept the effective override.
4. Implement tool-native per-turn projection and restore for supported headless backends.
5. Add CLI flags to `houmao-mgr agents turn submit`, `houmao-mgr agents gateway prompt`, and `houmao-mgr agents prompt`.
6. Update CLI and managed-agent API docs.

Rollback is straightforward because the change is additive:

- stop sending `execution`
- remove the new request parsing and CLI flags

No stored data migration is required.

## Open Questions

- Whether accepted turn or prompt responses should expose the resolved effective execution payload for observability without turning it into durable state.
- Whether queued gateway request refusal for TUI execution overrides should use a dedicated error code shared with direct prompt control or stay as generic validation failure.
