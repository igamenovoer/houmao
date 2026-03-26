## Context

`houmao-mgr agents launch` currently accepts an optional `--session-name`, but the runtime-owned default tmux naming contract is built around canonical agent identity plus an `agent_id` prefix. That rule is encoded in shared runtime helpers and applies to tmux-backed launch flows, while operator-facing usage increasingly centers on managed-agent names rather than internal `agent_id` material.

The requested change is not just a CLI help tweak. It changes the default persisted transport handle contract for tmux-backed managed launches, including the no-server `local_interactive` path used by `houmao-mgr` serverless interactive agents. The design therefore needs to update the shared naming helper, the launch-time collision rule, and the documentation/tests that currently assume agent-id-derived tmux handles.

This change also tightens the user-input side of managed-agent naming. Because the runtime now always owns the `AGENTSYS-` canonical namespace used in default tmux session names, operators should not be allowed to supply managed-agent names that already begin with a leading `AGENTSYS` token plus separator in any casing.

Just as importantly, the new tmux session name must stay an opaque transport handle. Its contract is limited to avoiding collisions with irrelevant tmux sessions and making Houmao-owned sessions recognizable during operator inspection. Discovery, listing, and agent-to-session mapping must continue to flow through shared-registry metadata rather than tmux session-name parsing or naked tmux enumeration heuristics.

User-facing name targeting should follow the same separation. Operators should target agents by the raw friendly name they created with `--agent-name`, not by the system-owned canonical `AGENTSYS-...` form.

## Goals / Non-Goals

**Goals:**
- Make the default tmux session name predictable from managed-agent identity and launch time.
- Use the canonical managed-agent name in `AGENTSYS-<name>` form plus a launch timestamp in epoch milliseconds.
- Make default-name collisions fail explicitly instead of mutating the candidate name to find another suffix.
- Reserve leading `AGENTSYS<separator>` user-provided managed-agent names for system canonicalization.
- Preserve explicit caller-provided `--session-name` as the override path.
- Cover the serverless `houmao-mgr` launch path, especially `local_interactive`.
- Preserve the shared-registry boundary for discovery and mapping; the tmux handle remains non-semantic.
- Preserve a clean user-facing distinction between raw friendly names and system-canonical `AGENTSYS-...` identities.

**Non-Goals:**
- Do not change canonical managed-agent naming or `agent_id` generation rules.
- Do not change explicit `--session-name` semantics beyond preserving existing validation.
- Do not add a retry loop, random suffix, or collision-recovery suffix expansion to the default naming path.
- Do not redesign registry discovery beyond consuming the persisted tmux session handle already recorded by the runtime.
- Do not ban every occurrence of `AGENTSYS` inside user-provided names; only the reserved leading namespace pattern is out of bounds.
- Do not introduce reverse-parsing of tmux session names or tmux-list-driven agent resolution as part of this change.
- Do not require operators to learn or type canonical `AGENTSYS-...` names when using `houmao-mgr ... --agent-name` targeting surfaces.

## Decisions

### 1. Default names derive from canonical agent name plus launch-time epoch milliseconds
The runtime will derive the default tmux session name as:

- `AGENTSYS-<normalized-agent-name>-<epoch-ms>`

This keeps the existing `AGENTSYS-` namespace signal that operators already use for managed agents while making the suffix human-explainable during interactive testing and troubleshooting.

Alternative considered:
- Keep the `agent_id`-prefix rule and only document it better.
  Rejected because the requested change is specifically about making the default easier to predict from operator-visible launch context.

### 2. Explicit `--session-name` remains authoritative
When the caller passes `--session-name`, the runtime will continue to use that explicit value instead of generating the timestamp-based default.

Alternative considered:
- Force all launches onto the timestamp format, ignoring explicit overrides.
  Rejected because operator-selected tmux handles remain useful for debugging and compatibility workflows.

### 3. User-provided managed-agent names reserve the leading `AGENTSYS<separator>` namespace
User-provided managed-agent names should be treated as the raw logical name portion, not as already-canonical values. A leading `AGENTSYS` token followed by a separator will be rejected case-insensitively at input validation time.

This means examples such as the following are invalid:

- `AGENTSYS-james`
- `agentsys-james`
- `AGENTSYS_james`

and examples such as the following remain valid:

- `AGENT-SYS-james`
- `james-AGENTSYS`
- `AGENTSYSTEM`
- `AGENTSYS123`

Alternative considered:
- Continue banning any standalone `AGENTSYS` token anywhere in the name.
  Rejected because it is broader than necessary and blocks names the user explicitly wants to allow.

### 4. Collision handling becomes fail-fast
If the generated default tmux session name already exists, launch fails with an explicit error. The runtime will not extend the suffix, append randomness, or retry with a different timestamp value inside the same launch attempt.

Alternative considered:
- Preserve the existing collision-resolution behavior by mutating the default candidate until it becomes unique.
  Rejected because it undermines the new contract that the default handle is exactly canonical name plus launch timestamp.

### 5. One shared helper should own the timestamp-based default
The existing shared tmux naming helper should become the source of truth for default tmux session-name derivation so `local_interactive` and headless tmux-backed launches do not drift.

This implementation should take the canonical managed-agent name plus an explicit launch timestamp value, rather than recomputing multiple time readings across layers.

Alternative considered:
- Implement separate default-name generation in `houmao-mgr agents launch` and leave backend helpers unchanged.
  Rejected because it would create divergent naming behavior across tmux-backed runtime launch paths.

### 6. Docs and tests should treat tmux session names as timestamp-based transport handles
Operator docs and tests that currently assume `agent_id`-derived tmux handles need to be updated to:

- describe the timestamp-based default,
- distinguish canonical agent name from persisted tmux session handle,
- state that the tmux handle exists for collision avoidance and operator visibility only,
- keep discovery/mapping guidance anchored on shared-registry metadata,
- make user-facing examples target agents by the raw `--agent-name` value rather than canonical `AGENTSYS-...` names,
- assert collision failure instead of suffix extension.

### 7. `--agent-name` targeting remains raw and unprefixed
For `houmao-mgr` managed-agent targeting surfaces, `--agent-name` should address the raw creation-time friendly name exactly as the operator supplied it during launch. The system should not require or encourage callers to supply canonical `AGENTSYS-...` names on these targeting surfaces.

Prefixed values such as `AGENTSYS-james` should be rejected on `--agent-name` selectors rather than silently normalized. This keeps the user-facing control contract consistent with creation-time naming and avoids exposing internal canonicalization details as an operator requirement.

Alternative considered:
- Accept both raw names and canonical `AGENTSYS-...` names on `--agent-name`.
  Rejected because it leaks internal canonicalization into the user-facing selector contract and increases ambiguity about which name is authoritative for operators.

## Risks / Trade-offs

- [Clock granularity collisions in the same millisecond] -> Fail explicitly and require the caller to retry or provide `--session-name`; do not silently change the generated name.
- [Input validation drifts from existing identity/control-path normalization] -> Scope the reserved-prefix rejection to user-provided managed-agent names for launch/build flows and keep control-path identity resolution behavior explicit in docs/tests.
- [The new handle format tempts callers to infer identity from tmux names] -> Re-state in spec/docs/tests that discovery, listing, and mapping remain shared-registry responsibilities and that tmux handles are opaque.
- [Canonical internal names leak into user-facing CLI targeting] -> Make `--agent-name` explicitly raw/unprefixed and reject prefixed forms in validation and docs.
- [Existing tests and docs assume agent-id-derived handles] -> Update spec-aligned tests and operator docs in the same implementation change.
- [Mixed historical manifests with old and new tmux handle formats] -> Keep discovery/control keyed off persisted manifest and registry metadata rather than reverse-parsing tmux handle format.
- [Implementation drift between `local_interactive` and headless tmux-backed paths] -> Centralize default-name derivation in one shared helper and cover both paths in tests.

## Migration Plan

1. Update the shared naming contract and launch-time helper logic.
2. Add launch-time validation that rejects user-provided managed-agent names beginning with `AGENTSYS` plus a separator, case-insensitively.
3. Update tmux-backed managed launch paths to use the shared timestamp-based default when `--session-name` is omitted.
4. Replace collision-extension behavior with explicit launch failure for generated default names.
5. Update `houmao-mgr` targeting validation so `--agent-name` uses raw creation names and rejects prefixed canonical forms.
6. Refresh docs and tests to reflect the new naming contract and the unchanged shared-registry discovery boundary.

Rollback is straightforward: revert the helper/spec change and restore the old agent-id-prefix default if needed.

## Open Questions

- Whether the epoch-millisecond suffix should be rendered strictly in UTC wall-clock capture time from Python `time.time_ns()`/`time.time()` conversion or another monotonic-plus-wall-clock combination. The current proposal assumes ordinary Unix epoch milliseconds from wall-clock time because that is what operators expect to read.
