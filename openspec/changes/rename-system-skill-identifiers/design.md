## Context

These four system skills are already treated as public packaged identifiers, not just internal directory names:

- `houmao-manage-agent-definition`
- `houmao-manage-agent-instance`
- `houmao-manage-credentials`
- `houmao-manage-specialist`

Their names currently appear in the packaged catalog, packaged asset subpaths, tool-home projected directories, Houmao-owned install-state records, system-skills CLI output, packaged skill cross references, focused tests, current docs, and current OpenSpec requirements.

That means this change is a coordinated rename across packaging, projection, reporting, and documentation. The repository already has one precedent for this style of migration: `houmao-create-specialist` was superseded by `houmao-manage-specialist` through installer-owned path migration rather than through long-lived aliasing.

The target names are:

- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-credential-mgr`
- `houmao-specialist-mgr`

The underlying `houmao-mgr` command families and skill boundaries are already in place and do not need redesign for this change.

## Goals / Non-Goals

**Goals:**

- Replace the four current packaged public skill identifiers with the renamed identifiers everywhere they are treated as current Houmao-owned system skills.
- Migrate Houmao-owned installed homes cleanly from the old projected directories and recorded names to the renamed ones.
- Keep the packaged catalog, skill metadata, cross-skill routing text, docs, tests, and current OpenSpec requirements consistent with the renamed identifiers.
- Preserve the current skill boundaries, named sets, and managed-home versus CLI-default install behavior.

**Non-Goals:**

- No redesign of the underlying `houmao-mgr` command surfaces or their flags.
- No new runtime alias surface that keeps the old skill names active indefinitely for `system-skills list`, install reporting, or packaged docs.
- No archive rewrite for historical OpenSpec changes or past release notes.
- No requirement to rename current OpenSpec capability folder names under `openspec/specs/`; this change only needs the current requirement text to name the active packaged skills correctly.

## Decisions

### 1. Treat this as a hard public-name cutover with owned-install migration, not as a dual-name compatibility phase

The current packaged catalog and `houmao-mgr system-skills` surfaces will present only the new identifiers as current:

- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-credential-mgr`
- `houmao-specialist-mgr`

Previously installed Houmao-owned homes will migrate forward on reinstall or auto-install by removing the old owned paths and recording only the new names.

Why:

- The previous `houmao-create-specialist -> houmao-manage-specialist` migration already established this pattern.
- Keeping both old and new names active would produce duplicate packaged identities for the same workflow and would complicate ownership tracking, docs, and tests.
- The user request is a rename, not an alias expansion.

Alternative considered:

- Keep the old names as installable aliases for one or more releases.
  Rejected because it would prolong mixed terminology and require the catalog, installer, docs, and skill references to recognize two public names for the same maintained skill.

### 2. Rename asset directories, catalog keys, and projected tool-home paths together

Each renamed skill will move as one unit:

- packaged directory name under `src/houmao/agents/assets/system_skills/`
- catalog key in `catalog.toml`
- `asset_subpath`
- projected tool-home directory name such as `skills/<name>/` or `.gemini/skills/<name>/`
- recorded install-state `name` and `projected_relative_dir`

Why:

- The installer contract already assumes that a current packaged skill’s `asset_subpath` equals its directory name.
- Partial renames would leave the catalog and projected paths harder to reason about and would weaken the flat “one skill name, one directory” packaging model.

Alternative considered:

- Keep old directory names and only change the display name in docs/metadata.
  Rejected because the packaged catalog and install-state model are path-based; a display-only rename would not deliver the requested cleanup.

### 3. Extend the existing rename-migration mechanism instead of inventing a second migration path

The shared installer already supports renamed skills through `_SYSTEM_SKILL_RENAMED_FROM`. This change will extend that mechanism so the new current names supersede the old ones and remove the previously owned projected directories during reinstall or auto-install.

Why:

- It matches the current install-state merge and ownership-removal model.
- It keeps migration behavior focused in one known installer seam.
- It gives tests one consistent way to validate rename handling.

Alternative considered:

- Write one-off migration code outside the shared installer.
  Rejected because it would fragment ownership logic and increase the risk of stale projected directories surviving in some install paths.

### 4. Update current docs and current specs in the same change, but leave archive history historical

The active README, system-skills overview, CLI reference, and current OpenSpec requirements will all be updated to use the renamed public identifiers. Archived changes and archived spec history will remain unchanged as historical records.

Why:

- Current operator-facing and developer-facing documentation should name the active packaged skills consistently.
- Archive content is supposed to preserve what was true when those changes were authored.

Alternative considered:

- Rewrite archive history to normalize every old identifier to the new naming.
  Rejected because it would blur historical context and add a large amount of unrelated churn.

### 5. Keep the current skill boundaries and set topology unchanged

This rename does not change which commands each skill routes to, which sets they belong to, or which sets are used for managed auto-install versus CLI-default install. The only behavior change is the public skill identity and the resulting owned-path migration.

Why:

- The existing scope split is already defined in current specs and skill content.
- Mixing a naming cleanup with boundary changes would make the migration harder to reason about and test.

Alternative considered:

- Use the rename to also regroup sets or broaden/narrow skill scope.
  Rejected because it would turn a bounded naming migration into a separate product-design change.

## Risks / Trade-offs

- [Explicit external references to the old skill names will break] → Treat the rename as explicitly breaking, update current docs/specs/tests in the same change, and avoid claiming old-name compatibility beyond owned-install migration.
- [Installed homes that are not reinstalled will keep old projected directories until touched again] → Run the migration inside the shared installer so the next explicit install, managed launch, or managed join refreshes those homes automatically.
- [Current OpenSpec capability folder names remain historically mismatched with the renamed public skills] → Keep the requirement text authoritative for the active packaged names and defer any capability-folder rename cleanup to a separate maintenance change if it becomes worth the churn.
- [Cross-skill references could drift if one skill is renamed without its neighbors] → Update all packaged skill content and doc inventory pages together rather than treating each directory rename in isolation.

## Migration Plan

1. Rename the four packaged skill directories and update their `SKILL.md`, action pages, references, and `agents/openai.yaml` metadata to use the new names in self-reference and cross-skill routing.
2. Update `catalog.toml`, related installer constants, and the shared rename map so the new names are the only current packaged identifiers and the old names are treated as superseded.
3. Update focused installer and `houmao-mgr system-skills` tests to assert the renamed inventory, projected directories, install-state records, and old-path migration behavior.
4. Update the current README, getting-started guide, CLI reference, and current OpenSpec spec text to use the renamed identifiers consistently.
5. Validate that reinstall or auto-install removes the old owned skill directories and records only the renamed identifiers.

Rollback:

- Restore the old packaged names and catalog entries in a follow-up change.
- Reinstall into affected tool homes if development rollback needs to project the old directories again.

## Open Questions

- None for proposal scope. The main deferred cleanup question is whether current OpenSpec capability folder names should eventually be renamed to match the public skill identifiers, but that is intentionally outside this change.
