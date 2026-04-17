## 1. Catalog And Runtime Defaults

- [x] 1.1 Add `houmao-utils-workspace-mgr` to the packaged system-skill catalog with a flat `asset_subpath`
- [x] 1.2 Replace granular named sets with `core` and `all` in `catalog.toml`
- [x] 1.3 Set managed launch and managed join auto-install lists to `core`
- [x] 1.4 Set omitted-selection CLI install defaults to `all`
- [x] 1.5 Update system-skill constants and callers to use the current `core` and `all` set names

## 2. Workspace Utility Skill

- [x] 2.1 Create the top-level `houmao-utils-workspace-mgr` skill asset
- [x] 2.2 Split in-repo workspace behavior into `subskills/in-repo-workspace.md`
- [x] 2.3 Split out-of-repo workspace behavior into `subskills/out-of-repo-workspace.md`
- [x] 2.4 Specify plan mode as dry-run by default with optional Markdown plan output
- [x] 2.5 Specify execute mode for workspace scaffolding, worktrees, shared repos, `workspace.md`, launch-profile cwd updates, and optional memo seed files
- [x] 2.6 Specify safe local-state symlink rules that skip AI tool state directories for Houmao workspaces
- [x] 2.7 Specify tracked-submodule materialization modes with `seeded-worktree` as the default

## 3. Documentation

- [x] 3.1 Update README system-skill coverage to include `houmao-utils-workspace-mgr` and the `core`/`all` set model
- [x] 3.2 Update the system-skills overview guide to organize skills as automation/control/utils while documenting only `core` and `all` as installable sets
- [x] 3.3 Update the system-skills CLI reference to show current list/install defaults and accepted set names
- [x] 3.4 Update managed-memory documentation so `houmao-memory-mgr` is described through the current `core` set
- [x] 3.5 Update utility skill wording that referenced the removed `utils` set

## 4. Verification

- [x] 4.1 Add regression coverage that installable system-skill sets are closed over internal skill-routing references
- [x] 4.2 Run targeted system-skill, CLI, and docs guard tests
- [x] 4.3 Run targeted Ruff checks for touched Python test/runtime files
- [x] 4.4 Run whitespace validation with `git diff --check`
- [x] 4.5 Validate the OpenSpec change in strict mode
