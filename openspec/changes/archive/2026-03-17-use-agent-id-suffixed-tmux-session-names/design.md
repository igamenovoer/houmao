## Context

The current runtime treats canonical agent identity and live tmux session handle as separate concepts, but the active runtime-owned start path still chooses an opaque tmux session name of the form `houmao-<session_id>`. Older helper paths and several tests/docs still assume the tmux session handle can equal the canonical `AGENTSYS-<name>` identity.

This change makes tmux session handles operator-readable while preserving the existing identity split:

- canonical agent identity stays `AGENTSYS-<name>`
- authoritative agent identity stays the full `agent_id`
- live tmux session handle becomes `<canonical-agent-name>-<agent-id-prefix>`

The change is cross-cutting because tmux naming flows through runtime start, backend constructors, manifest persistence, tmux-local discovery, shared-registry publication, and interactive demo state/reporting.

In this change, "tmux-backed" refers to the current tmux-backed backend set used by runtime identity and manifest validation:

- `codex_headless`
- `claude_headless`
- `gemini_headless`
- `cao_rest`

`codex_app_server` remains out of scope because the current runtime does not treat it as a tmux-backed backend.

## Goals / Non-Goals

**Goals:**

- Make live tmux session handles recognizable from the canonical agent identity.
- Make the handle deterministic from canonical `agent_name` plus authoritative `agent_id`.
- Keep canonical `AGENTSYS-<name>` addressing stable for runtime CLI operations.
- Preserve existing manifest and shared-registry discovery as the source of truth when tmux handle and canonical identity differ.
- Update interactive demo state, inspect output, and startup cleanup to work with the new tmux handle contract.

**Non-Goals:**

- Changing canonical agent naming rules or mailbox principal/address naming.
- Changing the authoritative `agent_id` derivation rule away from full MD5-by-default.
- Adding a new manifest or registry schema version solely for this rename.
- Supporting multiple concurrently live sessions for the same canonical `agent_name` and `agent_id`.
- Exposing a user-configurable tmux-name prefix length in this change.
- Making tmux session-name strings a reverse-parseable contract for canonical identity or agent-id recovery.

## Decisions

### Decision: Introduce one shared tmux-session-name derivation helper in `agent_identity.py`

The runtime should derive tmux session names from a single shared helper in `agent_identity.py` instead of continuing to mix:

- `houmao-<session_id>` in runtime start, and
- `AGENTSYS-<tool-role>[-N]` in older backend allocation helpers.

The helper should accept:

- canonical `agent_name`
- authoritative `agent_id`
- default prefix length `n=6`
- optional occupied-session set for uniqueness checks

Primary candidate:

- `<agent_name>-<agent_id[:6]>`

If that candidate collides with an occupied tmux session for a different live session, the helper should extend the `agent_id` prefix until the name becomes unique, up to the full authoritative `agent_id`. If uniqueness still cannot be achieved, startup should fail explicitly rather than silently creating an ambiguous handle.

Collision extension should proceed one additional `agent_id` character at a time (`6`, `7`, `8`, ...) so the result remains deterministic and easy to test.

`tmux_runtime.py` may keep a thin tmux-facing wrapper that delegates to this helper, but the old `AGENTSYS-<tool>-<role>[-N]` algorithm is retired in this change. No staged deprecation period is required.

Why this approach:

- keeps the common case short and readable
- preserves determinism from runtime-owned identity metadata
- avoids introducing another opaque runtime-specific identifier
- preserves the existing split between pure identity derivation and tmux command execution

Alternatives considered:

- Keep `houmao-<session_id>`: unique, but not operator-readable.
- Use `<agent_name>` only: readable, but collides immediately for replacement or concurrent sessions and loses authoritative identity.
- Use full `<agent_name>-<full-agent-id>`: deterministic, but unnecessarily long for normal tmux usage.

### Decision: Canonical agent identity remains the public address, tmux handle remains a separate runtime field

The CLI and manifest should continue to expose:

- `agent_identity` / `agent_name` as canonical `AGENTSYS-<name>`
- `agent_id` as authoritative identity
- `tmux_session_name` as the actual live tmux handle

This preserves the current conceptual split and avoids overloading canonical identity with transport/container details.

The tmux session handle should be treated as an opaque transport handle. Callers and tooling should discover it from persisted metadata rather than reverse-parsing canonical identity or agent-id components from the tmux session name string.

Why this approach:

- it matches existing manifest and registry structure
- it keeps mailbox and other identity-derived surfaces stable
- it avoids forcing callers to learn or reconstruct the tmux handle when they only need canonical agent addressing

Alternatives considered:

- Reinterpret canonical agent identity as the tmux handle: simpler string story, but it leaks tmux-specific suffixes into user-facing identity and breaks existing canonical identity semantics.

### Decision: Name-based resolution should treat exact-canonical tmux lookup as legacy compatibility, not the primary contract

Today local tmux resolution first checks whether a tmux session exists whose name exactly equals the canonical `AGENTSYS-<name>` identity. Under the new naming scheme, that direct match is no longer the primary runtime-owned case.

The updated resolution contract should be:

1. canonicalize the caller's name to `AGENTSYS-<name>`
2. optionally accept an exact-canonical tmux session only as a legacy compatibility path when it still exists and its manifest matches
3. otherwise inspect tmux-local discovery metadata to find the unique live tmux session whose manifest persists:
   - `agent_name == canonical identity`
   - `tmux_session_name == actual live tmux handle`
4. if tmux-local discovery is unavailable or stale, fall back to shared-registry resolution

Why this approach:

- it supports both new suffixed handles and older exact-name sessions during transition
- it preserves the existing manifest/env and shared-registry discovery model
- it avoids requiring callers to know the authoritative `agent_id` just to send a prompt

Alternatives considered:

- Reconstruct tmux handle from canonical name alone: fails for explicit `--agent-id` overrides and hides collision handling.
- Resolve by shared registry first: useful fallback, but weaker than tmux-local truth when the local session is live and already publishes exact env pointers.

### Decision: Manifest building must stop inferring canonical `agent_name` from tmux session name for tmux-backed runtime-owned sessions

The generic manifest builder still has compatibility fallbacks that can infer `agent_name` from `tmux_session_name`. That only works when both strings are interchangeable.

For runtime-owned tmux-backed sessions created by the main runtime, manifest construction should always receive explicit:

- canonical `agent_name`
- authoritative `agent_id`
- actual `tmux_session_name`

Compatibility inference can remain for legacy manifest upgrade or narrow helper/test flows, but it should not be relied on by the runtime-owned start path.

Why this approach:

- preserves clean semantics for persisted identity fields
- avoids accidentally persisting suffixed tmux handles as canonical agent names
- reduces hidden coupling between identity and transport naming

Alternatives considered:

- Continue deriving `agent_name` from `tmux_session_name`: incorrect once the tmux handle carries an id suffix.

### Decision: Interactive demo state and recovery should use persisted tmux handle data, not canonical identity, for tmux cleanup and attach guidance

The demo currently keeps both canonical `agent_identity` and tmux-facing fields such as `session_name` / `tmux_target`, but some cleanup and output paths still assume all three are the same string.

The demo should:

- preserve canonical `agent_identity` as the tutorial-facing name
- persist the actual tmux handle as `session_name` / `tmux_target`
- render `tmux attach -t <tmux_target>` from persisted tmux state
- stop stale sessions by canonical agent identity through runtime APIs
- clean orphaned tmux leftovers by persisted or discovered tmux metadata, not by assuming the canonical identity is a tmux target

When persisted demo state is missing, cleanup should enumerate tmux-local discovery metadata and match sessions whose persisted `agent_name` equals the canonical tutorial identity. An exact canonical tmux session name may still be cleaned as a legacy fallback, but cleanup should not remove sessions solely because their tmux session name shares a string prefix with the canonical tutorial identity.

Why this approach:

- keeps tutorial flows aligned with runtime behavior
- prevents stale suffixed tmux sessions from surviving replacement startup
- gives operators a correct attach command without making them infer the handle

Alternatives considered:

- Continue printing canonical identity in attach commands: simpler output, but wrong once the live tmux handle differs.

## Risks / Trade-offs

- `[Short-prefix collision]` Rare collisions are possible with a 6-character `agent_id` prefix. → Extend the prefix until unique and fail explicitly only if uniqueness cannot be achieved.
- `[Operator breakage]` Manual tmux commands that assume `AGENTSYS-<name>` is the live session name will stop working. → Update runtime/demo docs, troubleshooting docs, and demo inspect output to surface the actual tmux handle.
- `[Hidden legacy assumptions]` Tests and helper constructors may still infer canonical identity from tmux name. → Move the runtime-owned start path to explicit identity fields and update fixture helpers that currently rely on equality.
- `[Resolution complexity]` Name-based resolution becomes more metadata-driven and less direct. → Keep the legacy exact-name tmux check as a compatibility fast path while relying on persisted manifest and registry metadata as the durable truth.

## Migration Plan

1. Add the shared tmux-session-name helper and switch runtime-owned start flows to use it.
2. Update headless and CAO backend allocation helpers in the current tmux-backed backend set to use the same naming contract when no explicit tmux session name is supplied, retiring the old `AGENTSYS-<tool>-<role>` algorithm instead of carrying it forward in parallel.
3. Tighten manifest construction so runtime-owned tmux-backed sessions always persist explicit `agent_name`, `agent_id`, and `tmux_session_name`.
4. Update tmux-local name resolution to work when canonical agent identity and tmux handle differ, while preserving legacy exact-name compatibility.
5. Update interactive demo persisted state, inspect output, and startup cleanup to use the actual tmux handle plus metadata-backed cleanup discovery keyed by canonical identity.
6. Refresh docs and tests that currently assume `tmux_session_name == agent_name`.

Rollback approach:

- revert the shared naming helper and restore previous runtime tmux-name derivation
- because no schema bump is required, persisted manifests remain readable as long as they continue to carry explicit `tmux_session_name`

## Open Questions

- None for proposal readiness. The design assumes the default suffix length is fixed at 6 in this change and only grows automatically when uniqueness requires it.
