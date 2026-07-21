## Context

The actor-pack refactor introduced three public system skills and one protected routine tree. Public entrypoints establish an immutable admin or verified-agent frame before loading the protected `houmao-shared-routines` router. The implementation currently gives the protected router and every protected routine an exact `SKILL.md` filename, and the recursive validator requires that filename for all nested capabilities.

The current Imsight layout contract now assigns filenames by runtime role. A standalone or host-discoverable root owns `SKILL.md`; a capability nested under `subskills/<name>/` owns `SKILL-MAIN.md` and is loaded explicitly by its parent. A nested directory containing both filenames is invalid. This distinction prevents recursive exact-`SKILL.md` scanners from registering parent-scoped routines independently.

Houmao must adopt that convention without changing its three-skill public surface, actor rules, route arguments, or standalone top-level skill contracts elsewhere in the repository.

## Goals / Non-Goals

**Goals:**

- Make every protected router and routine parent-scoped and scanner-safe.
- Keep the admin welcome and both executable actor entrypoints host-discoverable.
- Make parent-to-child loading explicit, selective, and actor-frame preserving.
- Validate entrypoint roles and invocation-notation metadata before installation.
- Keep automatically generated mailbox prompts on public native skill triggers.
- Make existing receipt-owned compositions visibly stale and safely upgradeable.

**Non-Goals:**

- Rename public skill names or protected route arguments.
- Treat protected placement or Markdown instructions as an authorization boundary.
- Rename `SKILL.md` for project skills, private skills, generated top-level skills, the auto system-prompt skill, or legacy migration assets.
- Add `SKILL-SOURCE.md`; Houmao does not preserve upstream runtime entrypoints under `org/src/` in this asset tree.
- Add a managed-agent welcome skill or move protected routines beneath `houmao-admin-welcome`.

## Decisions

### 1. Preserve `SKILL.md` Only at Host-Discoverable Roots

The three public system skills remain top-level `SKILL.md` directories. Both protected route sources become `routes/<audience>/SKILL-MAIN.md`, and each protected routine becomes `subskills/<logical-id>/SKILL-MAIN.md`. The composer copies the selected route to the mounted `houmao-shared-routines/SKILL-MAIN.md` and copies routine trees without renaming files.

Using the same role-canonical name in source and composed trees makes package review and validation match runtime behavior. Keeping source route files named `SKILL.md` and renaming only while composing was rejected because it would preserve two filename semantics for the same object and make source validation weaker than installed validation.

The installed shape is:

```text
<public-entrypoint>/
├── SKILL.md
└── subskills/
    └── houmao-shared-routines/
        ├── SKILL-MAIN.md
        └── subskills/
            └── <protected-routine>/
                └── SKILL-MAIN.md
```

### 2. Centralize Role-Canonical Filenames in the Manifest Layer

The manifest module defines constants for public and parent-scoped entrypoint filenames. Frontmatter validation accepts an explicit entrypoint filename instead of assuming `SKILL.md`. Source validation, composition validation, route loading, and routine loading all use these constants.

Recursive subskill validation requires `SKILL-MAIN.md` for every direct child below any `subskills/` directory and rejects a sibling `SKILL.md`. Public-root validation requires `SKILL.md` and rejects a sibling `SKILL-MAIN.md`. Composition validation also scans exact `SKILL.md` paths and requires the public root to be the only match in each composed public skill.

Legacy nested `SKILL.md` is not accepted as a runtime compatibility input. The Imsight migration tooling may read it as source input, but Houmao packages canonical assets and therefore fails closed on obsolete or ambiguous layouts.

### 3. Make Each Parent the Only Router to Its Children

The admin and agent public entrypoints explicitly load `subskills/houmao-shared-routines/SKILL-MAIN.md` after establishing their actor frame. Each audience router exposes a table containing route name, exact child load path, and one `When to Route Here` sentence. After selecting a route, it loads only that child's `SKILL-MAIN.md` and the local commands or references needed for the selected operation.

Protected routines retain their actor-frame gates. The filename prevents accidental discovery, while the actor frame and runtime command validation remain responsible for behavior and authorization.

### 4. Enforce the Imsight Invocation-Notation Declaration

Any packaged instruction page that uses object-style designators such as `X->Y` or `X->Y->cmd()` receives the standard folded `skill_invocation_notation` frontmatter value. Pages without designators do not receive the key. The validator detects designator-bearing Markdown pages and rejects missing or non-standard declarations.

The placeholder `<public-entrypoint>` remains a source-time mechanism and is rendered to the selected public entrypoint during composition. The declaration describes the notation and canonical filenames; it does not convert internal arrow traces into public native triggers.

### 5. Keep Generated Prompts on Public Native Triggers

Mailbox command prompts and gateway notifier prompts continue to invoke only `houmao-agent-entrypoint`, using `$`, `/`, or plain tool-specific guidance as supported. The generated text states that the public entrypoint owns protected traversal and that protected routines must not be discovered or invoked independently.

The prompt code continues to test installation by checking the public entrypoint's top-level `SKILL.md`. It does not probe protected `SKILL-MAIN.md` paths because protected layout is an implementation detail and the composed pack validator guarantees the nested tree.

### 6. Version the New Composition Contract

The manifest schema advances from `houmao-system-skills.v2` to `houmao-system-skills.v3`. Receipt schema v1 remains readable because its structure does not change. Pack status compares the receipt's `manifest_schema_version` with the current manifest and marks receipt-owned public projections as drifted when they differ. An ordinary pack upgrade then replaces the complete receipt-owned public directory transactionally.

This avoids compatibility copies and gives operators a direct migration path. Rollback is the existing transactional backup restoration; source control can also restore the v2 package if required.

## Risks / Trade-offs

- [Some host clients may not understand `SKILL-MAIN.md` automatically] → Public `SKILL.md` entrypoints load nested files explicitly, so host discovery is required only for public roots.
- [Bulk frontmatter insertion can touch many instruction pages] → Use a deterministic transformation, validate every designator-bearing page, and run formatting-sensitive tests.
- [An existing home can retain a v2 tree until upgraded] → Manifest-version comparison marks the pack drifted and the documented upgrade command replaces the receipt-owned tree atomically.
- [A broad filename replacement could break ordinary skills] → Limit renames and validation changes to the packaged protected system-skill tree; retain existing top-level skill validators elsewhere.
- [Protected metadata files remain physically readable] → Continue documenting protected placement as a discovery boundary rather than a security boundary, and retain actor/runtime enforcement.

## Migration Plan

1. Rename protected route and routine source entrypoints without compatibility copies.
2. Update the manifest, schema, composer, validators, and parent routing instructions.
3. Update generated prompts, tests, fixtures, and documentation.
4. Install or upgrade each actor pack. Existing receipt-owned paths are replaced transactionally; unowned collisions still fail before mutation.
5. Verify that recursive exact-`SKILL.md` discovery sees only public roots and that old v2 receipts report drift until upgraded.

## Open Questions

None. Public invocation syntax, actor routing, and the migration mechanism remain fixed by the existing actor-pack design.
