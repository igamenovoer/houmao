## Context

`houmao-mgr` resolves most single-target managed-agent commands through `resolve_managed_agent_target()` in `src/houmao/srv_ctrl/commands/managed_agents.py`. That resolver intentionally treats `--agent-name` as a friendly managed-agent name, not as a tmux session handle, and it prefers local shared-registry discovery before falling back to the default pair authority.

The current failure path is misleading when local friendly-name lookup misses and the default pair authority is down. In that case, the operator sees only the pair-authority connection error even though the more actionable problem is usually one of these:

- the supplied `--agent-name` does not match any local friendly managed-agent name,
- the supplied value matches a tmux/session alias rather than the published managed-agent name, or
- the operator needs to disambiguate with `--agent-id`.

This resolver is shared across `agents`, explicit-target gateway commands, `agents mail`, and `agents turn`, so small changes here affect the entire operator-facing surface.

## Goals / Non-Goals

**Goals:**

- Preserve the existing selector contract: `--agent-name` means friendly managed-agent name.
- Make local selector misses visible even when remote pair fallback is unavailable.
- Provide exact alias hints when the operator supplied a tmux/session alias instead of the friendly name.
- Apply the improved error surface through the shared resolver so all explicit-target managed-agent commands benefit consistently.

**Non-Goals:**

- Expanding `--agent-name` to accept tmux session names, terminal ids, or other aliases as first-class selectors.
- Reworking remote `houmao-server` alias semantics in this change.
- Changing current-session targeting contracts.
- Changing successful resolution behavior for `--agent-id` or unique friendly-name matches.

## Decisions

### Keep `--agent-name` strict and improve diagnostics instead of broadening selector semantics

The existing contract in `houmao-srv-ctrl-native-cli` already says `--agent-name` targets the friendly managed-agent name. This change keeps that rule intact and makes failures explain the mismatch.

Why this over auto-resolving tmux/session aliases:

- It preserves the distinction between launch-time managed-agent identity and tmux hosting details.
- It avoids making local resolution more permissive than the documented CLI contract.
- It keeps the fix low-risk and focused on operator guidance rather than changing addressing semantics.

### Introduce a composite selector-resolution failure for local miss plus remote-unavailable fallback

When local registry-first discovery finds no record for the supplied friendly name, the resolver should retain that miss context. If default pair lookup then fails because no supported pair authority is reachable, the final error should combine both facts:

- no local friendly-name match was found, and
- remote pair lookup could not be attempted successfully.

Why this over returning the raw pair-authority error:

- The raw connectivity failure is true but incomplete.
- Operators can often correct the problem immediately once they know the selector itself is wrong.
- This mirrors the more operator-friendly posture already used by `houmao-mgr server status`, which degrades pair unavailability into a domain-specific message instead of surfacing transport details directly.

### Use exact local alias hints only as diagnostics

On a local friendly-name miss, the resolver should scan fresh local registry records for an exact match against tmux/session aliases such as `terminal.session_name`. If there is exactly one such match, the error should mention that the supplied value identifies a live local session alias, not the published managed-agent name, and should point to the corresponding `agent_name` and `agent_id`.

Why this over fuzzy matching or broader heuristics:

- Exact alias matches are precise and easy to explain.
- The registry already contains the needed identity fields.
- Fuzzy hints would risk suggesting the wrong agent or implying undocumented selector support.

### Centralize the new error shaping in the shared managed-agent resolver

The new behavior should live in `resolve_managed_agent_target()` and its helper path rather than being implemented separately in `agents show`, `agents prompt`, `agents mail`, and similar entrypoints.

Why this over per-command wrappers:

- The affected commands already share the resolver.
- Centralization keeps error wording consistent.
- Tests can target one resolver behavior plus a small number of command-level smoke cases.

## Risks / Trade-offs

- [Remote alias behavior remains more permissive than local friendly-name lookup] -> Document the preserved local contract clearly in the spec and keep this change limited to failure reporting.
- [Alias hints depend on fresh local registry records] -> Treat alias hints as best-effort diagnostics; the primary error remains the friendly-name miss.
- [Composite errors may become too verbose] -> Keep the message structured: local miss first, then optional alias hint, then remote-unavailable note, then retry guidance.
- [Shared resolver changes can affect many commands at once] -> Cover the resolver with unit tests and add targeted CLI failure assertions for representative commands.

## Migration Plan

No data migration is required. The implementation is an operator-facing error-surface refinement with accompanying unit and CLI contract tests.

## Open Questions

- Whether local and remote `--agent-name` resolution should eventually converge on one strict contract or one alias-aware contract remains open, but that semantics change is out of scope for this proposal.
