## Context

Upstream issue 32 asks for a supported lifecycle surface that sits between relaunch and brand-new launch: rebuild current Houmao-managed launch inputs, but keep the previous runtime home so provider-local history remains available. The repository already has most of the building blocks:

- low-level brain construction can reuse an existing home id,
- managed relaunch and stopped-session revival can reuse an existing home without rebuilding it,
- managed force takeover can recover a live predecessor home id during replacement launch.

What is missing is one operator-facing fresh-launch path that can intentionally bind those pieces together for local managed agents. The change must preserve the existing distinction between launch and relaunch, must not silently destroy preserved provider history, and should stay explicit and local-first.

## Goals / Non-Goals

**Goals:**

- Add one explicit launch-owned reuse-home mode to `houmao-mgr agents launch`.
- Add the same explicit reuse-home mode to `houmao-mgr project easy instance launch`.
- Rebuild current Houmao-managed launch material onto one compatible preserved home while creating fresh live session authority for the new launch.
- Keep provider-local history available through the preserved home without turning the new launch into relaunch.
- Fail clearly when reuse cannot be satisfied safely.

**Non-Goals:**

- Supporting arbitrary home adoption by raw path or home id in v1.
- Applying relaunch chat-session policy during reuse-home fresh launch.
- Supporting server-owned or remote-managed agents in v1.
- Supporting destructive `clean` semantics together with reuse-home.

## Decisions

### 1. Reuse-home remains a launch surface, not a relaunch surface

The operator-facing shape should be `--reuse-home` on `houmao-mgr agents launch` and `houmao-mgr project easy instance launch`, not an extension of `agents relaunch`.

Rationale:

- The requested semantics are "fresh launch inputs, old home data", which is still launch behavior.
- Existing relaunch and stopped-session revival are explicitly documented as reusing the already-built home rather than rebuilding current launch inputs.
- Keeping reuse-home on launch preserves the existing mental model:
  - `relaunch` = restart the same built session/home posture
  - `launch --reuse-home` = rebuild current launch inputs onto preserved home data

Alternatives considered:

- Add a new dedicated `restart` command. Rejected for v1 because the existing launch surfaces already own source/profile resolution and launch-time overrides.
- Extend `agents relaunch`. Rejected because it would blur the established relaunch contract and make stored relaunch chat-session policy ambiguous.

### 2. Reuse-home resolves predecessor state by managed identity from local lifecycle metadata

The implementation should resolve preserved-home candidates through existing local managed-agent lifecycle metadata, using the managed identity selected for the new launch.

Rationale:

- Managed identity resolution already exists and is the supported way to target live/stopped local sessions.
- Local lifecycle metadata already preserves manifest and brain-home identity fields for stopped sessions.
- Identity-based lookup avoids unsafe arbitrary adoption of unrelated homes.

Alternatives considered:

- Accept `--home-id` or raw filesystem paths on managed launch. Rejected for v1 because it weakens compatibility checks and makes operator mistakes easier.
- Pick the newest home for the matching tool automatically. Rejected because implicit home selection is too risky for a history-preserving feature.

### 3. Reuse-home is compatible only with non-destructive keep-stale behavior

`--reuse-home` should work with no force mode when the predecessor is already stopped, and with bare `--force` / `--force keep-stale` when a live predecessor must stand down first. It should reject `--force clean`.

Rationale:

- The requested feature exists specifically to preserve provider-local history in the preserved home.
- Destructive clean mode would remove that home and discard the history the operator asked to keep.
- The low-level builder already models this invariant by disallowing reuse-home together with clean-home behavior.

Alternatives considered:

- Allow `--reuse-home --force clean` and reinterpret it as partial cleanup. Rejected for v1 because the cleanup boundary would be subtle, tool-specific, and easy to misunderstand.

### 4. Fresh-launch semantics stay fresh even when the home is reused

Reuse-home launch should rebuild current Houmao-managed projections onto the preserved home, then start a new runtime session root and new live authority. It should not consume relaunch chat-session policy or provider-native continuation selectors automatically.

Rationale:

- The change is about preserving provider-visible state in the home, not about automatically selecting continuation mode.
- Launch-profile relaunch chat-session policy is already scoped to relaunch, and keeping that boundary avoids surprising startup behavior.
- Provider-native `/resume` or equivalent surfaces can still observe the preserved home after startup without Houmao pretending the launch was a relaunch.

Alternatives considered:

- Automatically translate stored relaunch chat-session policy into provider-start arguments for reuse-home launch. Rejected because it would make first launch from a reused home behave like relaunch.

### 5. Compatibility checks must happen before provider startup

Reuse-home launch should verify that the preserved home is compatible before starting the new provider runtime.

Compatibility should at minimum require:

- same local runtime root,
- same managed identity,
- same tool family as the current launch,
- preserved home path still present on disk.

Rationale:

- Early failure is safer than starting the provider and discovering home incompatibility later.
- Reusing existing local metadata keeps diagnostics concrete and actionable.

## Risks / Trade-offs

- [Risk] Preserved provider state may still conflict with updated credentials or config. → Mitigation: make reuse-home explicit, keep failure behavior clear, and avoid silent fallback to fresh-home launch.
- [Risk] Operators may confuse reuse-home launch with relaunch. → Mitigation: keep the CLI on launch surfaces, reject relaunch-only behavior, and document the distinction in launch lifecycle docs.
- [Risk] Non-destructive keep-stale behavior may leave stale provider artifacts that the refreshed launch does not touch. → Mitigation: keep this mode explicit, document its limits, and reserve deeper cleanup variants for future work.
- [Risk] Friendly-name ambiguity could select the wrong preserved state. → Mitigation: reuse existing managed-identity resolution rules and fail clearly on ambiguous local matches.

## Migration Plan

This change is additive and opt-in. No data migration is required.

Implementation rollout should:

1. Add the new CLI flags and reuse-home runtime plumbing.
2. Add coverage for stopped predecessor reuse, live predecessor reuse with `--force keep-stale`, and rejection cases.
3. Update launch lifecycle docs and launch-profile guidance so the new surface is clearly separated from relaunch.

Rollback is straightforward: remove the new flag handling and preserve the existing fresh-home default behavior.

## Open Questions

- Should successful launch output explicitly report the reused home id/path, or is the explicit `--reuse-home` flag plus existing manifest output sufficient for v1?
- Should a later iteration allow explicit reuse by manifest/session locator when managed-identity lookup is unavailable, or is identity-based selection enough for the supported lifecycle surface?
