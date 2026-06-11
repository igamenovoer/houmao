## Context

Houmao packages maintained system skills under `src/houmao/agents/assets/system_skills/` and declares the current installable inventory in `catalog.toml`. The catalog key is also the selected skill name, projected tool-home directory name, and visible name reported by `houmao-mgr system-skills`.

The existing `houmao-agent-ag-ui` skill already covers more than agent-specific AG-UI authoring. It teaches component schema discovery, payload validation, standard AG-UI event rendering, Houmao gateway publishing, active-thread fallback, GUI delivery interpretation, and safety rules. The desired current identity is `houmao-interop-ag-ui`.

This repository is under active unstable development, so the rename can be breaking. The system-skill catalog already supports `retired_skill_names`, which lets installs and syncs remove old Houmao-owned projections from tool homes.

## Goals / Non-Goals

**Goals:**

- Make `houmao-interop-ag-ui` the only current installable name for this packaged skill.
- Remove current code, tests, docs, and OpenSpec references that present `houmao-agent-ag-ui` as current.
- Treat `houmao-agent-ag-ui` as a retired skill projection so managed homes and explicit installs clean up stale old-name directories.
- Preserve the existing AG-UI authoring and publishing behavior under the new skill identity.

**Non-Goals:**

- Do not rename AG-UI protocol routes, `houmao-mgr internals ag-ui`, gateway publish subcommands, workbench paths, package names, or protocol constants.
- Do not provide a compatibility alias that installs both `houmao-agent-ag-ui` and `houmao-interop-ag-ui`.
- Do not rewrite archived OpenSpec history unless a separate archive-maintenance change asks for that.

## Decisions

### Use a hard current-name rename

The catalog should replace `[skills.houmao-agent-ag-ui]` with `[skills.houmao-interop-ag-ui]`, update `asset_subpath`, and update the `core` and `all` set membership. The packaged asset directory and `SKILL.md` frontmatter `name` should match the new catalog key.

Alternative considered: keep `houmao-agent-ag-ui` as an alias. That would preserve old selectors but would also make `system-skills list`, status reporting, and managed-home synchronization ambiguous. A hard rename fits the repo's current breaking-change policy and keeps one public identity.

### Retire the old projection name

The catalog should add `houmao-agent-ag-ui` to `retired_skill_names`. The existing cleanup path removes known retired projections during install and sync, so users who reinstall or relaunch through Houmao get stale old-name directories removed without a special migration command.

Alternative considered: leave old projections untouched. That would avoid filesystem deletion, but agents could discover both names and follow stale prompts. Retired cleanup is already the project pattern for removed system skills.

### Rename the OpenSpec capability

The current `openspec/specs/houmao-agent-ag-ui-skill/` capability should become `openspec/specs/houmao-interop-ag-ui-skill/` during implementation. The change delta introduces the new capability and updates installation, CLI, and docs requirements that depend on the current name.

Alternative considered: keep the old capability folder and only change its text. That would preserve OpenSpec history but would keep the stale public name in current spec inventory.

### Keep protocol and UI product names stable

Only the Houmao system-skill identity changes. Names such as `ag-ui`, `AG-UI`, `houmao-mgr internals ag-ui`, `/v1/ag-ui/*`, `apps/ag-ui-workbench`, `houmao.graphic.template`, and `houmao_render_graphic` remain protocol, route, package, or component names and should not be renamed by this change.

## Risks / Trade-offs

- Stored project or launch-profile policies may explicitly select `houmao-agent-ag-ui` -> Those selectors will become invalid under the hard rename. The direct fix is to update stored selectors to `houmao-interop-ag-ui` rather than adding an alias.
- Existing tool homes may still contain the old copied skill until install or sync runs -> Adding the old name to `retired_skill_names` lets normal Houmao install/sync paths remove it.
- Search-and-replace can accidentally rename protocol paths such as `/v1/ag-ui` -> Implementation should limit textual replacement to the system-skill identity and reviewed OpenSpec/docs references.
- Archived OpenSpec changes will still mention the old name -> Treat archive text as historical unless a separate archive rewrite is requested.

## Migration Plan

1. Move the packaged asset directory from `houmao-agent-ag-ui` to `houmao-interop-ag-ui`.
2. Update catalog current inventory, set membership, constants, tests, and current docs/specs.
3. Add `houmao-agent-ag-ui` to `retired_skill_names`.
4. Update active unarchived OpenSpec change artifacts that still identify the current skill by the old name.
5. Run focused system-skill tests and OpenSpec validation.

Rollback is a normal code revert before release. After users install the renamed skill, rollback would require reinstalling the older package version because retired cleanup may have removed old-name projected directories.

## Open Questions

None. The change intentionally uses the repository's breaking-change policy rather than preserving old selectors.
