## Why

Houmao currently exposes several overlapping loop-authoring skills (`pairwise`, `pairwise-v2` through `v5`, and `generic`) even though `houmao-agent-loop-pro` now covers both tree-loop and generic-loop execplan workflows. Keeping the older loop skills current increases install weight, documentation complexity, routing ambiguity, and test maintenance without adding a clear user-facing path.

## What Changes

- **BREAKING**: Retire the legacy packaged loop skills from the current system-skill inventory:
  - `houmao-agent-loop-pairwise`
  - `houmao-agent-loop-pairwise-v2`
  - `houmao-agent-loop-pairwise-v3`
  - `houmao-agent-loop-pairwise-v4`
  - `houmao-agent-loop-pairwise-v5`
  - `houmao-agent-loop-generic`
- Add `houmao-agent-loop-pro` to the packaged system-skill catalog and the `core` / `all` install sets.
- Make `houmao-agent-loop-pro` the only current Houmao loop-authoring and loop-execution guidance skill.
- Route both tree-loop and generic-loop topology work through pro topology modes instead of separate package names.
- Move retired loop skill source trees into a source-only legacy reference directory under `src/` instead of deleting them.
- Do not reference retired loop skills from the current catalog, current docs, project-scope symlinks, or maintained routing guidance. Users who truly need an old skill must handle that legacy source manually.
- Update project-scope skill symlinks for Codex, Claude, and Copilot so loop skill discovery exposes pro only.
- Update touring, advanced-usage, README, getting-started, CLI reference, internals-graph reference, and example docs to stop presenting pairwise/generic loop packages as current choices.
- Preserve historical terminology and already-authored artifacts as legacy references where needed, but do not keep retired package names as current installable skills.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-system-skill-installation`: current catalog and install-set requirements replace legacy loop skills with `houmao-agent-loop-pro`.
- `houmao-mgr-system-skills-cli`: list/install/status behavior surfaces pro as the current loop skill and no longer reports retired loop skills as current inventory.
- `houmao-agent-loop-pro-skill`: pro becomes the sole maintained loop skill for tree-loop and generic-loop authoring, generated execplan validation, and generated loop execution.
- `houmao-agent-loop-pairwise-skill`: stable pairwise skill is retired from current packaged inventory.
- `houmao-agent-loop-pairwise-v2-skill`: pairwise-v2 skill is retired from current packaged inventory.
- `houmao-agent-loop-pairwise-v3-skill`: pairwise-v3 skill is retired from current packaged inventory.
- `houmao-agent-loop-pairwise-v4-skill`: pairwise-v4 skill is retired from current packaged inventory.
- `houmao-agent-loop-pairwise-v5-skill`: pairwise-v5 skill is retired in favor of pro.
- `houmao-agent-loop-generic-skill`: generic loop skill is retired in favor of pro generic-loop mode.
- `houmao-loop-terminology`: pairwise/generic package names become historical or compatibility references, while current guidance names pro topology modes.
- `houmao-adv-usage-pattern-skill`: composed topology and run-control escalation routes to pro.
- `houmao-touring-skill`: advanced loop tour routes to pro instead of enumerating legacy loop packages.
- `docs-readme-system-skills`: README system-skill inventory and loop narrative describe pro as the current loop skill.
- `docs-system-skills-overview-guide`: system-skills overview describes pro as the loop control skill.
- `docs-loop-authoring-guide`: loop authoring guide becomes pro-oriented and describes tree-loop/generic-loop mode selection inside pro.
- `docs-cli-reference`: CLI reference current skill inventory replaces legacy loop package entries with pro.
- `docs-internals-graph-cli-reference`: graph tooling docs refer to pro authoring and legacy mode aliases where relevant.
- `writer-team-example`: runnable example points operators at pro instead of pairwise.
- `system-files-reference-docs`: pairwise-v2 runtime files are marked legacy/historical if still documented.

## Impact

- Affected skill catalog: `src/houmao/agents/assets/system_skills/catalog.toml`.
- Affected skill assets: move retired loop skill directories to a source-only legacy reference directory; keep `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/` as the only current loop skill asset.
- Affected project skill symlinks: `.codex/skills/`, `.claude/skills/`, `.github/skills/`.
- Affected docs: README, loop authoring guide, system-skills overview/reference, internals graph reference, writer-team example, and system-files docs.
- Affected tests: system-skill catalog/install tests, brain-builder auto-install tests, docs guard tests, and loop-skill content tests.
- No runtime database migration is required for the retirement itself.
