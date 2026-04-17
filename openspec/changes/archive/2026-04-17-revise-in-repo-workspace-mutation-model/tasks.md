## 1. Skill Guidance

- [x] 1.1 Update `subskills/in-repo-workspace.md` so the default launch cwd is `<repo-root>` and the per-agent `repo/` path is described as the source/shared-KB mutation surface rather than the process cwd.
- [x] 1.2 Add an in-repo read/write ownership table covering parent source, own worktree, own worktree shared KB, parent shared KB, own KB, sibling KB, sibling worktrees, and `workspace.md`.
- [x] 1.3 Update in-repo plan requirements to require launch cwd, visibility surface, and safe write targets.
- [x] 1.4 Update in-repo execute steps so launch profiles are adjusted to `<repo-root>` for in-repo workspaces and generated `workspace.md` records ownership rules.
- [x] 1.5 Update in-repo merge guidance so source and shared-KB changes merge from private worktree branches while agent-owned parent KB changes are treated as direct owner notes.
- [x] 1.6 Update top-level `SKILL.md` launch-profile, memo-seed, and `workspace.md` guidance so selected workspace flavors can define different planned cwd values and in-repo memo seeds include safe write targets.

## 2. Requirements And Tests

- [x] 2.1 Update or add unit coverage for the packaged workspace-manager asset to assert the in-repo skill text includes the repo-root cwd and private-mutation contract.
- [x] 2.2 Ensure existing system-skill projection tests still pass with the revised packaged asset content.
- [x] 2.3 Run `openspec status --change revise-in-repo-workspace-mutation-model` and confirm the change is apply-ready after implementation.

## 3. Verification

- [x] 3.1 Run `pixi run test tests/unit/agents/test_system_skills.py`.
- [x] 3.2 Run `pixi run test tests/unit/srv_ctrl/test_system_skills_commands.py` if projection or packaging behavior changes beyond text assertions.
