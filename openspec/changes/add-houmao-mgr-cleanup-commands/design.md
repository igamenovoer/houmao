## Context

Houmao currently exposes only one operator-facing cleanup command through the native CLI: `houmao-mgr admin cleanup-registry`, which removes stale shared-registry directories by lease or malformed-state classification. That leaves several other cleanup workflows undocumented or manual:

- stopped runtime session roots and their optional workspace-local job dirs,
- unreferenced build artifacts under `<runtime-root>/homes/` and `<runtime-root>/manifests/`,
- past gateway or server log artifacts,
- session-local mailbox secret files,
- runtime-owned Stalwart credential files that are no longer referenced,
- inactive or stashed filesystem mailbox registrations that are no longer relevant.

At the same time, Houmao already has enough metadata to make these operations safer than ad hoc `rm -rf`:

- runtime session manifests point at `job_dir`, `brain_manifest_path`, and mailbox bindings,
- build manifests point at `runtime.home_path`,
- tmux-backed managed sessions publish `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, and `AGENTSYS_AGENT_DEF_DIR`,
- gateway attach and relaunch already use manifest-first current-session resolution inside the owning tmux session,
- mailbox registration state persists active, inactive, and stashed registrations separately from canonical message history.

This change is therefore cross-cutting. It touches the native CLI tree, registry cleanup semantics, runtime artifact classification, and mailbox lifecycle cleanup semantics.

## Goals / Non-Goals

**Goals:**

- Add a coherent cleanup command surface to `houmao-mgr` instead of leaving cleanup as one-off manual filesystem work.
- Support `--dry-run` across cleanup operations so operators can inspect candidates, preserved artifacts, and blocked deletions before execution.
- Reuse existing manifest-first current-session authority for agent-scoped cleanup when the operator runs a cleanup command inside the tmux session that hosts the managed agent.
- Keep cleanup local to the owning host and local filesystem roots; do not require new `houmao-server` admin endpoints.
- Distinguish cleanup classes carefully: live state, resumable durable state, log-style state, scratch state, and secret-bearing mailbox artifacts.
- Preserve canonical mailbox message content while allowing cleanup of inactive or stashed mailbox registrations and unreferenced runtime-owned mailbox credentials.

**Non-Goals:**

- Introduce an automatic garbage collector, background janitor, or startup-time pruning daemon.
- Add remote cleanup through `houmao-server` or passive-server APIs.
- Delete or rewrite live runtime sessions by default.
- Treat mailbox repair as the same operation as cleanup; `mailbox repair` remains the recovery path for rebuilding index state.
- Redefine durable gateway state such as `queue.sqlite` as disposable log output in this change.

## Decisions

### Decision 1: Split cleanup by authority and scope

The canonical cleanup tree will be:

```text
houmao-mgr admin cleanup registry
houmao-mgr admin cleanup runtime sessions
houmao-mgr admin cleanup runtime builds
houmao-mgr admin cleanup runtime logs
houmao-mgr admin cleanup runtime mailbox-credentials

houmao-mgr agents cleanup session
houmao-mgr agents cleanup logs
houmao-mgr agents cleanup mailbox

houmao-mgr mailbox cleanup
```

Authority split:

- `admin cleanup ...` is host-scoped and root-scoped local maintenance.
- `agents cleanup ...` is manifest-scoped local maintenance for one managed-agent session.
- `mailbox cleanup` is mailbox-root-scoped cleanup for filesystem mailbox registrations.

Rationale:

- Host-wide runtime roots, one resolved managed-agent session, and one filesystem mailbox root do not share the same resolution rules or safety model.
- The current-session defaulting requirement only makes sense for agent-scoped cleanup, not for host-wide janitors.
- Mailbox registration cleanup belongs with the mailbox CLI because it operates on one filesystem mailbox root and must preserve mailbox-specific invariants.

Alternatives considered:

- One large `houmao-mgr cleanup ...` top-level tree: rejected because it would mix host-local runtime cleanup, session-local cleanup, and mailbox-root cleanup into one ambiguous authority boundary.
- Only add `admin` janitors and make operators pass explicit paths for session cleanup: rejected because it would ignore the existing current-session manifest resolution model and keep the most common interactive cleanup path awkward.

### Decision 2: Keep cleanup local-only and add `--dry-run` as the preview contract

Cleanup commands remain local maintenance commands. They do not accept `--port` and do not require `houmao-server`.

Each cleanup command supports `--dry-run`, which returns structured planning data instead of deleting anything.

The result shape is unified across cleanup commands:

- `dry_run`
- `scope`
- `resolution`
- `planned_actions`
- `applied_actions`
- `blocked_actions`
- `preserved_actions`
- `summary`

Each action record carries at least:

- artifact kind,
- path,
- proposed action,
- reason.

Rationale:

- The user explicitly wants `--dry-run`.
- Cleanup is destructive enough that operators need a stable preview contract.
- A shared result shape lowers implementation and documentation complexity across command families.

Alternatives considered:

- Default to dry-run and require `--apply`: rejected for v1 because the user explicitly asked for `--dry-run`, and the CLI already uses ordinary execute-by-default semantics for local maintenance commands.
- Plain text human summaries only: rejected because cleanup planning is better exposed as machine-readable output for tests and operator tooling.

### Decision 3: `agents cleanup ...` reuses manifest-first current-session resolution

Agent-scoped cleanup commands accept one of these authorities:

- explicit `--agent-id`,
- explicit `--agent-name`,
- explicit `--manifest-path`,
- explicit `--session-root`,
- implicit current-session resolution when none of the above are provided and the command is run inside the owning tmux session.

Implicit current-session resolution reuses the same manifest-first logic already used by gateway attach and relaunch:

1. read `AGENTSYS_MANIFEST_PATH`,
2. if unavailable or stale, fall back to `AGENTSYS_AGENT_ID` and exactly one fresh shared-registry record,
3. validate that the resolved manifest belongs to the current tmux session,
4. derive the session root and related artifact paths from that manifest.

Derived defaults from the resolved manifest include:

- `session_root`,
- `job_dir`,
- `brain_manifest_path`,
- build-home references from the brain manifest,
- session-local mailbox secret directory,
- mailbox binding metadata when present.

Rationale:

- The repository already treats `AGENTSYS_MANIFEST_PATH` plus shared-registry fallback as the supported current-session authority.
- Cleanup should not invent a second session-discovery contract.
- Explicit `--manifest-path` and `--session-root` remain necessary after a session has already been stopped and no longer has a live registry entry.

Alternatives considered:

- Require explicit selectors for all `agents cleanup` commands: rejected because it ignores the user request and duplicates work current-session flows already do.
- Resolve cleanup targets through pair-managed server APIs: rejected because these commands remove local runtime-owned artifacts and should not depend on remote pair topology.

### Decision 4: Cleanup classification is reference-aware, not age-only

Cleanup decisions will use ownership and reference analysis before deletion:

- Registry cleanup uses missing/malformed/expired classification, plus optional local liveness probing for tmux-backed records.
- Session cleanup blocks deletion when the session still appears live on the local host.
- Build cleanup removes only build-manifest/runtime-home pairs that are unreferenced by preserved session manifests, or obviously broken half-pairs.
- Log cleanup removes only log-style or ephemeral artifacts and does not redefine durable queue or state contracts as scratch.
- Runtime mailbox credential cleanup removes only Stalwart credential files whose `credential_ref` is not referenced by any preserved session manifest.
- Mailbox registration cleanup touches only inactive or stashed registrations and never canonical `messages/` content.

For runtime-family host cleanup, the age knobs are explicit:

- `registry`: `--grace-seconds`
- `runtime sessions`, `runtime builds`, `runtime logs`, `runtime mailbox-credentials`: `--older-than-seconds`
- `mailbox cleanup`: `--inactive-older-than-seconds` and `--stashed-older-than-seconds`

Rationale:

- Paths alone are not enough; Houmao persists enough metadata to avoid deleting things that are still referenced.
- Different artifact families have materially different cleanup sensitivity.

Alternatives considered:

- Age-only cleanup for every artifact family: rejected because it would eventually delete still-referenced build artifacts and mailbox credentials.
- Treat every stopped session artifact as disposable scratch: rejected because the docs and runtime model intentionally keep many stopped-session artifacts for later inspection or resume-adjacent workflows.

### Decision 5: Separate mailbox registration cleanup from runtime mailbox-secret cleanup

Mailbox-related cleanup is split three ways:

- `mailbox cleanup` handles inactive or stashed filesystem mailbox registrations inside one mailbox root.
- `agents cleanup mailbox` handles session-local mailbox secret material for one resolved managed-agent session.
- `admin cleanup runtime mailbox-credentials` handles runtime-owned Stalwart credential files that are no longer referenced.

`mailbox cleanup` preserves:

- canonical message files under `messages/`,
- active registrations,
- mailbox roots that still need `repair` instead of purge.

Rationale:

- Filesystem mailbox registration lifecycle and runtime-owned credential lifecycle are different storage domains with different safety checks.
- Session-local mailbox secret cleanup can be derived directly from a resolved session manifest, while root-wide registration cleanup cannot.

Alternatives considered:

- Put every mailbox-related cleanup under `houmao-mgr mailbox cleanup`: rejected because runtime-owned Stalwart credential files live under the runtime root, not under the mailbox root.
- Make `mailbox repair` absorb stale registration cleanup: rejected because repair is recovery-oriented and intentionally preserves evidence and canonical content boundaries.

### Decision 6: `admin cleanup-registry` remains available as a compatibility alias while docs move to `admin cleanup registry`

The documented command path becomes `houmao-mgr admin cleanup registry`.

The existing `houmao-mgr admin cleanup-registry` spelling remains as a local compatibility alias during the transition so current tests and operator habits do not break unnecessarily while the new grouped cleanup tree is introduced.

Rationale:

- The grouped cleanup tree is cleaner and scales to additional janitors.
- Retaining the old direct spelling lowers migration churn for a small implementation cost.

Alternatives considered:

- Hard replace `cleanup-registry` immediately: rejected because the alias is cheap and avoids gratuitous CLI breakage while the larger cleanup surface lands.

## Risks / Trade-offs

- [Risk] Reference scanning misses a live dependency and proposes deleting a still-needed build or credential artifact. → Mitigation: derive references from preserved manifests first, keep live-session blockers, and expose the exact reasoning in `--dry-run` output.
- [Risk] Optional registry liveness probing could misclassify a live session as dead when tmux visibility is incomplete. → Mitigation: keep probe-based dead-session classification explicit and separate from the existing lease-based stale classification.
- [Risk] The cleanup tree becomes too broad to learn quickly. → Mitigation: keep the split by authority (`admin`, `agents`, `mailbox`) and use a shared result schema and consistent flag names.
- [Risk] Operators treat `logs` cleanup as permission to remove durable gateway state. → Mitigation: document and enforce that `logs` cleanup excludes durable gateway artifacts such as `queue.sqlite`.
- [Risk] Mailbox cleanup could be confused with repair and accidentally framed as message deletion. → Mitigation: keep `mailbox cleanup` scoped to inactive or stashed registrations and state explicitly that canonical messages are preserved.

## Migration Plan

1. Add shared cleanup result models and path-classification helpers.
2. Introduce `admin cleanup ...` and keep `admin cleanup-registry` as an alias to `admin cleanup registry`.
3. Implement `agents cleanup ...` with manifest-first current-session resolution and explicit path authority options.
4. Implement `mailbox cleanup` for inactive or stashed registration cleanup.
5. Update CLI, registry, and system-files documentation to use the grouped cleanup tree and to explain cleanup boundaries clearly.
6. Remove the compatibility alias in a later cleanup-focused change if the repository no longer needs it.

## Open Questions

No open questions remain for this change after the design decisions above.
