## Context

The repository still carries five CAO-oriented demo packs that are no longer needed:

- `scripts/demo/cao-claude-session/`
- `scripts/demo/cao-codex-session/`
- `scripts/demo/cao-claude-tmp-write/`
- `scripts/demo/cao-claude-esc-interrupt/`
- `scripts/demo/cao-dual-shadow-watch/`

Only two active capability specs directly require those paths today:

- `openspec/specs/cao-claude-demo-scripts/spec.md`
- `openspec/specs/cao-dual-shadow-watch-demo/spec.md`

Archived change artifacts also mention these demos, but those files are historical record rather than active contract. The older CAO dual-shadow-watch flow already has a maintained successor in `scripts/demo/houmao-server-dual-shadow-watch/` and the active capability `houmao-server-dual-shadow-watch-demo`.

## Goals / Non-Goals

**Goals:**

- Remove the obsolete demo packs from the live repository surface.
- Retire the active OpenSpec requirements that still obligate those demo packs to exist.
- Remove direct live implementation, tests, and docs that become invalid once the demo packs are deleted.
- Preserve a clear migration path toward maintained demo surfaces where one exists.
- Leave archived OpenSpec history intact.

**Non-Goals:**

- Rewriting or deleting archived change artifacts under `openspec/changes/archive/`
- Creating replacement demos for the retired CAO session packs
- Changing the maintained `houmao-server-dual-shadow-watch` capability beyond references needed for migration clarity

## Decisions

### 1. Retire active specs and live repo surfaces together

The demo directories and the active specs that require them will be removed in the same change. Removing only the files or only the specs would leave the repository in an inconsistent state.

Alternative considered:
- Remove the demo files first and leave the specs for a later cleanup. Rejected because it would knowingly leave broken active requirements behind.

### 2. Remove the entire `cao-claude-demo-scripts` active capability

Every current requirement in `cao-claude-demo-scripts` is anchored to the retired CAO session demos, either by requiring the demo-pack directories themselves or by constraining their shadow-mode extraction behavior. The cleanest change is to retire the entire active capability rather than trying to preserve a partial shell around demos that no longer exist.

Alternative considered:
- Rewrite the capability around a different maintained demo. Rejected because that would redefine the capability rather than retire it, and the repository already has separate active specs for maintained demo flows.

### 3. Remove the old CAO dual-shadow-watch capability and point migration at the Houmao-server demo

The old CAO dual-shadow-watch pack is superseded by the active `houmao-server-dual-shadow-watch-demo` capability. The removal delta for `cao-dual-shadow-watch-demo` should explicitly direct maintainers to the Houmao-server variant instead of leaving the capability without guidance.

Alternative considered:
- Keep the old CAO dual-watch spec as archive-like documentation. Rejected because active specs are normative and should not describe removed paths.

### 4. Treat archived references as intentional historical record

Archived proposal, design, task, review, and delta-spec files that mention the retired demos will remain untouched. This keeps change history auditable and avoids mixing implementation cleanup with archive rewriting.

Alternative considered:
- Search-and-remove archive references. Rejected because it rewrites historical artifacts and is outside the requested active-surface cleanup.

### 5. Remove direct references from active docs, tests, and inventories

After deleting the demo assets and active specs, the repository should not leave direct non-archive references to those demo paths in current docs, active inventories, or tests. The implementation should update or delete those references as part of the same change.

Alternative considered:
- Leave stale references for later cleanup. Rejected because it creates avoidable follow-up churn and weakens the value of the removal.

## Risks / Trade-offs

- [Risk] A live doc, checklist, or test still references a removed path after cleanup. -> Mitigation: run targeted repository searches and clean every non-archive reference in the same implementation.
- [Risk] Operators lose discoverability for manual shadow-watch validation. -> Mitigation: point migration guidance for the retired dual-watch capability at `houmao-server-dual-shadow-watch-demo`.
- [Risk] Some CAO session-demo use case no longer has a one-to-one replacement. -> Mitigation: state clearly in the removal delta that the retired directories should not be expected to exist, and point to maintained demo workflows where they cover adjacent needs.

## Migration Plan

1. Delete the retired demo directories and old dual-watch implementation/test surfaces.
2. Remove the corresponding active spec files from `openspec/specs/`.
3. Update active docs and inventories so they no longer point at removed paths.
4. Preserve archive references unchanged.

Rollback is straightforward before merge: restore the deleted demo assets and active specs. No data migration is involved.

## Open Questions

None.
