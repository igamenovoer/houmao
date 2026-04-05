## Context

Houmao-owned system skills currently live under `src/houmao/agents/assets/system_skills/` but the tree has started to grow family subdirectories such as `mailbox/` and `project/`. The shared installer mirrors that structure into visible tool homes for Codex by deriving a namespace from `asset_subpath`, which produces paths like `skills/mailbox/<skill>/` and `skills/project/<skill>/`.

That family-aware layout is not a stable cross-tool contract. Claude Code's `/skills/` loader expects `skill-name/SKILL.md`, Gemini CLI only discovers `SKILL.md` or `*/SKILL.md`, and Codex is more permissive but still documents and tests the flat `skills/<skill>/SKILL.md` model. Houmao-specific family nesting therefore creates a portability gap and turns packaged grouping into externally visible filesystem structure.

The recent `houmao-create-specialist` work also widened the mismatch by introducing a second family. Existing installed homes may now already contain Houmao-owned state that records old family paths, so flattening is not just a tree move inside the repo; it also requires explicit owned-path migration.

## Goals / Non-Goals

**Goals:**

- Make packaged Houmao-owned system skills use a flat top-level asset layout.
- Make installed Houmao-owned system skills use each tool's native top-level skill root without family subdirectories.
- Preserve logical grouping through explicit skill names, named sets, and catalog metadata instead of filesystem namespaces.
- Migrate existing Houmao-owned installed paths safely when a home still contains recorded `mailbox/` or `project/` paths.
- Update mailbox/runtime references, docs, and tests so they rely only on the flat contract.

**Non-Goals:**

- Renaming current Houmao-owned skills or removing the `houmao-` naming convention.
- Changing the meaning of the mailbox or `houmao-create-specialist` skill content beyond the path and installation contract.
- Introducing dynamic catalog rules, family metadata, or per-tool path overrides beyond what the flat layout requires.
- Preserving backward compatibility for repo-owned docs, tests, prompts, or local homes that still depend on `skills/mailbox/...` or `skills/project/...`.

## Decisions

### Decision: Package every Houmao-owned system skill directly under the asset root

Each skill directory will live directly under `src/houmao/agents/assets/system_skills/<skill-name>/`, and each catalog `asset_subpath` will equal that skill name.

Rationale:

- it matches the native mental model used by the supported agent tools,
- it removes family prefixes from the installer's source of truth,
- it makes packaged layout and visible installed layout tell the same story.

Alternatives considered:

- Keep `mailbox/` and `project/` directories in the repo but flatten only on install.
  Rejected because it keeps Houmao-specific family structure in the catalog and installer and invites the same drift again later.
- Add an explicit `family` metadata field while keeping flat install paths.
  Rejected because the grouping problem is already solved by named sets and the extra field would add maintenance without changing behavior.

### Decision: Project every Houmao-owned system skill into the native top-level skill root for its tool

The installer will project:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Gemini: `.agents/skills/<houmao-skill>/`

No supported tool will receive a visible family subdirectory such as `mailbox/` or `project/`.

Rationale:

- it matches Claude and Gemini loader contracts directly,
- it treats Codex recursion as an implementation detail rather than as a namespace design license,
- it keeps Houmao-owned skill identity in the reserved skill name instead of in an extra path segment.

Alternatives considered:

- Keep the Codex mailbox subtree because current mailbox prompts already know it.
  Rejected because it preserves a tool-specific special case that is no longer justified once non-mailbox skills exist.
- Keep family-aware projection only for Codex.
  Rejected because it makes the shared installer encode different conceptual layouts for the same packaged skill set.

### Decision: Preserve grouping only through names and catalog sets

Mailbox-oriented and project-oriented groupings will remain visible in named sets such as `mailbox-full` and `project-easy`, not as directory prefixes.

Rationale:

- sets already express install intent and default bundles,
- `houmao-` skill names already provide a collision-resistant reserved namespace,
- grouping in catalog data is meaningful while grouping in flat install targets is not.

Alternatives considered:

- Rename skills to add category prefixes beyond `houmao-`.
  Rejected because the current names are already explicit enough and further renaming would create unnecessary churn.

### Decision: Migrate old owned paths during install without changing install-state shape

The current install-state format already records each skill name and the owned projected relative directory. When reinstalling, if an existing Houmao-owned record for a selected skill points at an old family path and the current projection differs, the installer will remove the previously owned path before writing the new flat path and updated state.

Rationale:

- the existing state payload contains enough information to identify and clean up old owned paths,
- a schema bump would add migration code without changing the stored data model,
- safe cleanup can stay limited to paths that were previously recorded as Houmao-owned.

Alternatives considered:

- Bump the install-state schema and require a full state migration.
  Rejected because the payload shape is still sufficient.
- Leave old family directories behind and only update future installs.
  Rejected because it would preserve stale Houmao-owned paths and keep collision behavior ambiguous.

### Decision: Update mailbox runtime contracts to treat Codex like the other native flat tools

Mailbox runtime helpers, prompts, docs, and tests will stop referring to a visible Codex mailbox subtree and will instead rely on top-level Houmao-owned skill names under the active skill root.

Rationale:

- mailbox skills are still distinguishable by reserved names,
- the runtime already uses shared installer helpers for path resolution,
- the flat contract simplifies cross-tool prompting and reduces path-specific documentation.

Alternatives considered:

- Keep mailbox-specific wording in the mailbox runtime spec while flattening only the installer internals.
  Rejected because it would leave the public contract internally inconsistent.

## Risks / Trade-offs

- [Repo-owned prompts, docs, and tests still mention `skills/mailbox/...` or `skills/project/...`] → Update those references in the same change and treat any leftover family-path wording as a bug.
- [Owned-path cleanup could remove the wrong content] → Remove only paths that are inside the resolved tool home and already recorded as Houmao-owned install-state entries.
- [Flattening increases the chance of collision with user-authored skills] → Keep the reserved `houmao-` naming convention and continue to fail closed on non-owned path collisions.
- [The completed `add-houmao-create-specialist-skill` change currently documents the opposite design] → Revise or supersede those change artifacts before archive so OpenSpec history does not carry conflicting contracts.

## Migration Plan

1. Flatten the packaged system-skill asset tree and catalog `asset_subpath` values to one directory per skill.
2. Remove family-derived projection logic from the shared installer and make Codex project to `skills/<houmao-skill>/`.
3. Add install-time cleanup for previously owned family-namespaced skill paths before updating install state.
4. Update mailbox runtime references, CLI docs, tests, and the packaged `houmao-create-specialist` skill to use the flat path contract.
5. Validate installation and reinstall behavior for Claude, Codex, and Gemini homes, including migration from an existing family-path install-state file.

## Open Questions

- None. The remaining work is design execution and migration cleanup rather than product-scope clarification.
