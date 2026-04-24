## Context

`project easy specialist create|set --with-skill` delegates to the project skill registry, and the registry currently supports both copy-backed and symlink-backed canonical skill entries under `.houmao/content/skills/<name>`. The reported data-loss path appears when an existing canonical entry is symlink-backed to a caller-owned source directory and a later refresh goes through copy mode: the implementation resolves the canonical destination path before destructive replacement, so the deletion step can follow the symlink onto the caller-owned source tree.

The project skill registry is the right abstraction boundary for fixing this because both `project skills add|set` and easy-specialist `--with-skill` reuse it. The required behavior is strict: operator-provided source paths are read-only inputs, and only Houmao-managed content inside the selected project overlay may ever be deleted, replaced, or rolled back.

## Goals / Non-Goals

**Goals:**

- Enforce a hard ownership boundary so skill registration mutates only Houmao-managed overlay content.
- Prevent resolved-symlink deletion of caller-owned source directories when switching or refreshing project skills.
- Keep copy-backed and symlink-backed canonical skill modes working as before from the operator perspective.
- Make failure handling safe: partial cleanup may touch `.houmao/` state, but must never touch the provided source path.
- Add regression coverage for the exact symlink-backed canonical-entry refresh path reached through `--with-skill`.

**Non-Goals:**

- Redesigning the project skill registry model or removing `--with-skill`.
- Changing the meaning of `copy` versus `symlink` mode.
- Making every catalog content writer transactional in this change.
- Expanding the change into unrelated managed-content subsystems unless they are reached by the same unsafe helper path.

## Decisions

### 1. Treat caller-provided skill paths as read-only inputs

All flows that accept `--with-skill <dir>` or `project skills add|set --source <dir>` will treat that path as caller-owned input. The registry may read from it and may record it in metadata, but destructive operations must never target it directly.

This gives the fix a simple invariant to encode in code and tests: if a path came from the operator, Houmao does not delete, rewrite, or move it.

Alternatives considered:

- Document `--with-skill` as unsafe for symlink-backed registrations. Rejected because the observed behavior is destructive and violates basic ownership expectations.
- Keep current behavior but fail earlier when a skill is already registered. Rejected because the root bug is unsafe path targeting, not only duplicate registration.

### 2. Destructive replacement must operate on lexical Houmao-managed paths, not resolved targets

The registry should stop calling `.resolve()` on managed destination paths before remove-and-replace operations in the project-skill materialization flow. The deletion target must remain the lexical canonical path inside `.houmao/content/skills/<name>`, so replacing a symlink-backed canonical entry removes the symlink node instead of the symlink target.

This directly addresses the root cause while preserving supported `copy` and `symlink` semantics.

Alternatives considered:

- Keep using `.resolve()` and special-case symlink deletion. Rejected because it keeps the dangerous default and makes future callers easier to get wrong.
- Forbid mode changes once a skill is symlink-backed. Rejected because changing between `copy` and `symlink` is an intentional supported registry feature.

### 3. Add an ownership guard for destructive mutation helpers used by skill registration

The project-skill update path should centralize destructive writes through helpers that can verify the target path is inside Houmao-managed roots for the active overlay before deletion or replacement proceeds. The guard should cover the canonical content path and any derived projection path touched by the same registration/update flow.

This keeps the bug from reappearing through adjacent refactors and makes the “only Houmao-managed content can be mutated” rule executable rather than purely documentary.

Alternatives considered:

- Fix only the single `.resolve()` call with no guard. Rejected because the ownership boundary is a user-visible safety requirement and should be defended in code, not only by convention.

### 4. Failure cleanup stays local to the overlay

If a registration or `--with-skill` flow fails after replacing canonical or derived Houmao-managed paths, cleanup and rollback should be limited to those overlay paths. The implementation does not need a full transaction system for this fix, but it must never attempt to “restore previous state” by mutating the caller-owned source directory or anything reached through resolved symlink targets.

This keeps the fix scoped while still covering the reported failure mode.

Alternatives considered:

- Introduce a full transactional staging layer for all project content mutations. Rejected because it is broader than required for the immediate safety fix.

## Risks / Trade-offs

- [A narrow fix could miss another skill-registration path that still resolves managed destinations before deletion] → Mitigation: audit all helper calls used by `project skills add|set` and easy `--with-skill`, and add regression tests for both direct registry use and easy-specialist entrypoints.
- [Adding ownership guards could reject legitimate overlay mutations if the allowed-root calculation is wrong] → Mitigation: keep the allowed roots explicit and limited to the active overlay’s canonical content and derived projection roots, then test both copy-backed and symlink-backed updates.
- [Overlay state may still be partially updated after a failed registration] → Mitigation: accept Houmao-owned partial mutation for this change, but specify and test that caller-owned source paths remain untouched.

## Migration Plan

1. Update project-skill materialization so destructive replacement targets the lexical managed destination path instead of the resolved symlink target.
2. Add managed-root ownership checks around destructive helper paths used by skill registration and derived projection refresh.
3. Add regression tests for direct `project skills set` and easy `specialist create|set --with-skill` against already-registered symlink-backed skills.
4. Update any directly related command help or user-facing docs if they describe `--with-skill` behavior in a way that implies source mutation is acceptable.

## Open Questions

- Whether the ownership guard should remain narrowly scoped to project skill registration helpers in this change or be generalized to other catalog content writers in a later follow-up.
- Whether a future follow-up should make `--with-skill` prefer binding an already registered skill name when the provided source path matches the recorded source path, instead of always routing through update semantics.
