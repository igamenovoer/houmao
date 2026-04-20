## 1. Skill Policy Text

- [x] 1.1 Update `houmao-utils-workspace-mgr/SKILL.md` to replace the `.pixi`-only default with recursive local-state discovery for in-repo workspaces.
- [x] 1.2 Document `.pixi/` as a reachable default-allow exception that is not discovered under skipped hidden local-only parents.
- [x] 1.3 Document hidden local-state skip behavior for dot-prefixed paths at every depth, including `.env`, `.github`, AI-tool homes, and arbitrary hidden local directories or files.
- [x] 1.4 Document that symlinked directories are not followed during discovery.
- [x] 1.5 Document recursive tracked-content conflict checks and destination tracked-content conflict checks.
- [x] 1.6 Update `subskills/in-repo-workspace.md` if needed so the in-repo flavor page points clearly to the expanded local-state symlink policy.

## 2. Specification And Documentation Consistency

- [x] 2.1 Ensure the main `houmao-utils-workspace-mgr-skill` spec reflects reachable `.pixi/`, non-hidden local-only candidates, hidden parent precedence, symlink traversal limits, and recursive tracked-content checks.
- [x] 2.2 Review README and system-skill overview docs for any wording that conflicts with the expanded local-state symlink behavior.
- [x] 2.3 Keep out-of-repo wording consistent with the shared policy without implying a new runtime implementation engine.

## 3. Tests

- [x] 3.1 Update packaged skill asset tests to assert the workspace-manager skill mentions recursive local-state discovery.
- [x] 3.2 Add assertions that `.pixi/` remains default-allowed while hidden local-state paths are skipped by default.
- [x] 3.3 Add assertions that hidden parent precedence, symlinked directory traversal limits, and recursive tracked-content checks are documented.

## 4. Validation

- [x] 4.1 Run focused system-skill tests covering `houmao-utils-workspace-mgr`.
- [x] 4.2 Run `pixi run openspec validate expand-workspace-local-state-symlinks --strict`.
- [x] 4.3 Run `pixi run lint`.
