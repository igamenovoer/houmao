## Context

Houmao manages several filesystem subtrees that may legitimately contain symlinks: project overlay content and compatibility projections, shared-registry entries, server-managed headless authority trees, and some mailbox-style artifacts. The recent `--with-skill` fix proved that a local pattern of `destination = managed_root / relative_path; destination.resolve(); destructive_replace(destination)` is unsafe because resolving the managed artifact path before removal turns a symlinked artifact into its target.

The audit showed that this is not isolated to project skills. Similar patterns remain in catalog content writers, auth-profile removal, project migration, credential bundle mutation, shared-registry cleanup, and server-managed headless authority cleanup. The implementation needs one consistent rule for when symlinks may be followed for reads and when they must be treated as opaque artifacts.

## Goals / Non-Goals

**Goals:**
- Define one repository-wide contract for safe filesystem mutation in the presence of symlinks.
- Ensure Houmao mutates only Houmao-owned lexical paths for destructive operations such as replace, unlink, rename, and recursive delete.
- Ensure caller-provided or external source paths are treated as read-only inputs unless a workflow explicitly transfers ownership.
- Make cleanup flows verify containment before deleting managed artifacts, even when directories or entries are symlink-backed or malformed.
- Add regression coverage for the main mutation families so symlink escape bugs do not regress one surface at a time.

**Non-Goals:**
- Ban all symlink usage in Houmao-managed trees.
- Rewrite every path-normalization call site that only performs read-only inspection.
- Change the semantic meaning of existing commands beyond tightening their filesystem safety guarantees.
- Introduce backward-compatibility shims for unsafe legacy behavior.

## Decisions

### 1. Split path handling into read authority and mutation authority

Destructive operations will use **mutation authority** rules:
- operate on lexical artifact paths under an explicitly allowed Houmao-owned root;
- never call `resolve()` on the artifact being deleted or replaced;
- delete the artifact itself if it is a symlink;
- reject mutation when the lexical artifact path is outside the allowed root.

Read-side validation and import logic may still use **read authority** rules:
- resolve caller-provided inputs to inspect the concrete source content;
- verify required files, directories, or invariants on the resolved source;
- avoid converting that resolved source into the mutation target for managed cleanup.

This separation matches the real ownership model: external inputs may be followed for reads, but managed artifacts must be mutated lexically.

**Alternatives considered**
- *Resolve everything, then check containment*: rejected because it still turns a symlink artifact into its target, which is exactly the bug class we are trying to eliminate.
- *Ban symlink-backed managed artifacts*: rejected because several maintained flows intentionally use symlink projection or source-linked storage.

### 2. Introduce shared owned-path mutation helpers and require call sites to declare allowed roots

The implementation will centralize destructive path operations behind shared helpers that:
- compute lexical absolute paths;
- validate that the artifact path is equal to or nested under one of the allowed managed roots;
- remove or replace files, trees, and symlinks without dereferencing the artifact path first.

Call sites must supply the owned roots they are allowed to mutate. This makes the ownership boundary explicit in project catalog, credentials, cleanup, registry, and server authority code instead of relying on convention.

**Alternatives considered**
- *Patch each call site independently*: rejected because the risk is systemic and ad hoc fixes are likely to miss future paths.
- *Rely only on path-component sanitization*: rejected because sanitized names do not protect against pre-existing symlink artifacts.

### 3. Treat managed content references as semantic locators, not deletion targets

Content references may still resolve for reading payloads or computing digests, but delete/replace flows for managed content will derive the lexical artifact path from `(managed_root / relative_path)` instead of deleting `content_ref.resolve(...)`. This applies to project skills, auth payloads, memo seeds, setup snapshots, prompt overlays, and derived projection trees.

**Alternatives considered**
- *Continue using `resolve_under_content_root()` everywhere*: rejected because it is safe for reads but unsafe as a destructive target when the managed artifact is symlink-backed.

### 4. Define contained-cleanup rules for registry and server-owned state

Cleanup-oriented subsystems will use one of two safe models:
- lexical owned-root mutation helpers for known artifact paths, or
- resolve-plus-containment-check when the code must validate a selected path before mutation.

Either model is acceptable so long as deletion remains bounded to an owned root and never follows an artifact symlink into external space.

This preserves working server patterns such as session-registration containment checks while aligning older cleanup surfaces with the same policy.

**Alternatives considered**
- *Use lexical-only mutation everywhere*: rejected as too rigid because some cleanup selectors naturally resolve user-provided manifest/session paths before validation.

### 5. Cover the change with subsystem-focused regressions

The regression plan will target the bug classes rather than only one command:
- catalog replacement/removal with symlink-backed managed content;
- migration from legacy skill projections when the source or canonical artifact is symlink-backed;
- credential and cleanup removal when managed entries are symlinks;
- shared-registry and server-managed authority cleanup containment.

This keeps the safety contract anchored to executable behavior instead of only helper implementation.

## Risks / Trade-offs

- **[Risk] Broad helper adoption touches multiple subsystems** → **Mitigation:** keep the contract narrow (owned lexical mutation only) and apply it first to destructive paths rather than all path resolution.
- **[Risk] Some legacy flows may currently rely on following managed symlinks during deletion** → **Mitigation:** treat that behavior as invalid and make the specs explicit that only the artifact path, not its target, is owned for mutation.
- **[Risk] Read-side `resolve()` can still raise on symlink loops during validation** → **Mitigation:** document that as a separate read-path concern and add targeted handling only where user-visible workflows need clearer errors.
- **[Risk] Spec surface could become too fragmented across commands** → **Mitigation:** define one new cross-cutting safety capability and keep each modified existing capability focused on its externally visible filesystem guarantee.

## Migration Plan

1. Add the owned-path mutation safety capability and update the affected command/server specs.
2. Refactor destructive helpers and call sites to use the owned lexical mutation model.
3. Add regression coverage for each affected subsystem before broad cleanup refactors continue elsewhere.
4. Sync the finalized delta specs back into the main spec set once implementation is complete.

## Open Questions

- Should path-digest and integrity-report logic treat symlink-backed managed content as a first-class storage shape, or is it sufficient to keep current read semantics and only harden mutation?
- Should cleanup helpers across runtime, registry, and mailbox converge on one shared module, or should mailbox retain its parallel helper set because it models mailbox artifacts differently?
