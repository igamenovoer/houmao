## Context

The `remove-source-migration-paths` refactor (commit b18817e4) deleted session manifest v2 and v3 JSON Schema files, removed all in-memory manifest upgrade logic, and bumped the canonical schema version to 4. The on-disk schemas directory now contains only `session_manifest.v1.schema.json` and `session_manifest.v4.schema.json`.

Two documentation files were not updated to reflect this:

1. `docs/reference/system-files/agents-and-runtime.md` (line 71) still says `schema_version=2` and (line 78) describes the loader as rejecting only `schema_version=1`, when it now rejects anything ≠ 4.
2. `openspec/specs/brain-launch-runtime/spec.md` (line 806) uses `session_manifest.v3.schema.json` as an example filename, but that file no longer exists.

## Goals / Non-Goals

**Goals:**

- Update stale schema version numbers and example filenames to match current reality (v4).
- Ensure the operational note about manifest rejection matches the current strict-equality check.

**Non-Goals:**

- No code changes.
- No changes to other docs pages (README, CLI ref, getting-started guides are already current).
- No structural changes to the spec or doc files beyond the version number corrections.

## Decisions

1. **Update version numbers in-place rather than removing the sentences.** The statements about schema version and loader behavior are still useful context for readers; only the version numbers are wrong. Rationale: removing the sentences would lose valuable operational guidance.

2. **Update the spec example to reference `session_manifest.v4.schema.json`.** This is the current highest-version schema file on disk and matches what the builder actually emits. Alternative considered: referencing `v1` instead — rejected because v4 is the current write format and the more useful example.

3. **Widen the operational note's rejection description.** The note currently says "rejects legacy `schema_version=1`"; the accurate statement is that the loader rejects any version other than 4. This is more future-proof and matches the strict-equality check in `manifest.py`.

## Risks / Trade-offs

- **[Risk: version bumps again soon]** → The schema version may bump again before 1.0. Acceptable: the same pattern of updating these references applies, and the change is trivially small.
- **[Risk: spec file churn]** → Editing the spec example is cosmetic but keeps spec scenarios truthful. Acceptable trade-off for spec accuracy.
