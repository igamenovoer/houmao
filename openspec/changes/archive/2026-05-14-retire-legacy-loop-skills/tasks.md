## 1. Catalog And Installer

- [x] 1.1 Add `houmao-agent-loop-pro` to `src/houmao/agents/assets/system_skills/catalog.toml` as the only current loop skill.
- [x] 1.2 Remove retired loop skill names from current catalog `[skills]`, `core`, and `all` selections.
- [x] 1.3 Add catalog/schema or loader support for known retired Houmao-owned skill names, covering the five pairwise packages plus `houmao-agent-loop-generic`.
- [x] 1.4 Update system-skill install/reinstall logic to remove exact retired loop skill projections from selected target homes while installing current selections.
- [x] 1.5 Update system-skill status output to report retired loop leftovers separately from current installed skills.
- [x] 1.6 Update system-skill uninstall logic to remove current Houmao-owned projections and known retired loop projections.

## 2. Skill Assets And Project Scope

- [x] 2.1 Move retired loop skill directories into a source-only legacy reference directory under `src/`.
- [x] 2.2 Ensure the legacy reference directory is not treated as a packaged skill asset root by catalog loading, validation, or installers.
- [x] 2.3 Remove retired loop skill symlinks from project-scope `.codex/skills`, `.claude/skills`, and `.github/skills`.
- [x] 2.4 Ensure project-scope Codex, Claude, and Copilot skills retain only `houmao-agent-loop-pro` for loop authoring/execution.

## 3. Skill Guidance And Routing

- [x] 3.1 Update `houmao-agent-loop-pro` guidance only if needed so it clearly owns current tree-loop and generic-loop authoring/execution without routing to retired packages.
- [x] 3.2 Update `houmao-adv-usage-pattern` routing to send composed topology, generated execplan, and run-control needs to `houmao-agent-loop-pro`.
- [x] 3.3 Update `houmao-touring` guidance to present pro as the current advanced loop path and tree-loop/generic-loop as pro modes.
- [x] 3.4 Remove current-routing references to retired loop skill packages from maintained skill text outside the source-only legacy directory.

## 4. Documentation And Examples

- [x] 4.1 Update README system-skill inventory, loop narrative, and auto-install prose to list pro as the current loop skill.
- [x] 4.2 Rewrite the loop authoring guide around `houmao-agent-loop-pro`, with tree-loop/generic-loop mode selection inside pro.
- [x] 4.3 Update the system-skills overview and CLI reference to remove retired loop packages from current inventory and document retired projection cleanup.
- [x] 4.4 Update internals graph docs to describe pro as the current loop-skill consumer while preserving graph helper mode aliases where still accepted.
- [x] 4.5 Update the writer-team example to route current loop operation through pro and identify tree-loop behavior.
- [x] 4.6 Mark retained pairwise-v2 runtime-file documentation as legacy where those paths remain documented.

## 5. Tests

- [x] 5.1 Update system-skill catalog and loader tests to expect pro-only current loop inventory.
- [x] 5.2 Update system-skill install/status/uninstall command tests to cover retired loop projection cleanup and status reporting.
- [x] 5.3 Update brain-builder auto-install tests to expect `houmao-agent-loop-pro` and not retired loop packages.
- [x] 5.4 Update skill-content tests to stop reading retired package assets from the current skill root and to validate pro routing instead.
- [x] 5.5 Update docs guard tests for README, loop authoring, system-skills overview/reference, internals graph, writer-team, and system-files references.

## 6. Verification

- [x] 6.1 Run `pixi run test tests/unit/agents/test_system_skills.py tests/unit/srv_ctrl/test_system_skills_commands.py tests/unit/agents/test_brain_builder.py`.
- [x] 6.2 Run affected docs tests, including `pixi run test tests/unit/docs`.
- [x] 6.3 Run `pixi run lint` if implementation changes Python code.
- [x] 6.4 Run a final `rg` check outside archived changes and the legacy reference directory to confirm retired loop skill names are not presented as current routes.
