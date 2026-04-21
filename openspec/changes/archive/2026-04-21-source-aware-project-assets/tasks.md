## 1. Catalog And Projection Foundation

- [x] 1.1 Add project skill registry metadata to the catalog and model `.houmao/content/skills/<name>` as the canonical project skill entry with `copy|symlink` mode.
- [x] 1.2 Rework project compatibility materialization so `.houmao/agents/skills/` is rebuilt as derived projection from canonical project skill entries instead of acting as a peer live tree.
- [x] 1.3 Add explicit project-migration detection boundaries so ordinary catalog initialization and project-aware materialization fail with migration guidance instead of mutating legacy project structure implicitly.
- [x] 1.4 Add focused catalog and projection tests for copied skill entries, symlinked skill entries, and broken or missing symlink targets.

## 2. Project Migration CLI

- [x] 2.1 Add `houmao-mgr project migrate` command wiring under the top-level `project` family with plan-first behavior and explicit apply mode.
- [x] 2.2 Implement the initial supported migration set, including legacy `.houmao/easy/specialists/*.toml` import and compatibility-tree-first project skill migration into canonical `.houmao/content/skills/<name>`, with successful migration removing the replaced legacy project files.
- [x] 2.3 Add unsupported-layout detection and clear failure reporting for project states that fall outside the supported migration set.
- [x] 2.4 Add CLI tests for migration planning, explicit apply, migrated specialist import, migrated project skill canonicalization, replaced legacy-file removal, and unsupported-layout failure.

## 3. Project Skills CLI

- [x] 3.1 Add `houmao-mgr project skills add|set|list|get|remove` command wiring under the top-level `project` family.
- [x] 3.2 Implement `project skills add|set` source validation, default `copy` mode, explicit `symlink` mode, and canonical output reporting for `.houmao/content/skills/`.
- [x] 3.3 Implement safe `project skills remove` behavior that fails clearly while specialists still reference the target skill.
- [x] 3.4 Add CLI tests for project skill registration, inspection, update, and protected removal.

## 4. Easy Specialist And Runtime Integration

- [x] 4.1 Add name-based specialist skill binding on `project easy specialist create`, including `--skill <name>` and registry-backed `--with-skill <dir>` convenience behavior.
- [x] 4.2 Rework `project easy specialist set --add-skill|--with-skill|--remove-skill|--clear-skills` to operate on registered project skills rather than direct specialist-owned imports.
- [x] 4.3 Update specialist inspection payloads and launch/build plumbing so specialist skill references resolve through the project skill registry and runtime-facing projections symlink from canonical project skill entries where supported.
- [x] 4.4 Add unit or integration coverage for registry-backed specialist create, set, get, and launch flows in both `copy` and `symlink` modes.

## 5. Docs And Verification

- [x] 5.1 Update getting-started docs to describe `.houmao/content/skills/` as the canonical project skill root, `.houmao/agents/skills/` as derived projection, `project skills ...` as the maintained registry surface, and `project migrate` as the supported upgrade path for older overlays.
- [x] 5.2 Update the easy-specialists guide to teach skill registration before specialist binding, including `copy|symlink` operator intent, the maintained meaning of `--with-skill`, and the explicit migration path for older easy-specialist metadata.
- [x] 5.3 Add verification notes or targeted manual checks covering specialist launches from both copied and symlinked project skills, plus relaunch after project-skill edits in symlink mode and one end-to-end `project migrate` conversion path.
