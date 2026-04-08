## 1. Package the new project-management skill

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-project-mgr/` with a top-level `SKILL.md` plus the action/reference material needed for project init/status, launch-profile management, easy-instance `list|get|stop`, overlay resolution, `.houmao/` layout, project-aware effects, and renamed-skill routing boundaries.
- [x] 1.2 Update the packaged system-skill catalog and any companion schema or loader expectations so `houmao-project-mgr` is installable and included in the `user-control` set.

## 2. Update install-surface reporting and docs

- [x] 2.1 Update `houmao-mgr system-skills` reporting, tests, or snapshots so list/install/status surfaces reflect the expanded `user-control` set and the ten-skill packaged inventory.
- [x] 2.2 Update `docs/reference/cli/system-skills.md` to document `houmao-project-mgr`, its project-management boundary, its renamed-skill handoffs, and the updated CLI-default versus managed auto-install behavior.
- [x] 2.3 Update `README.md` and `docs/getting-started/system-skills-overview.md` so the packaged skill catalog, counts, and default-install explanations include `houmao-project-mgr`.

## 3. Verify the new packaged skill contract

- [x] 3.1 Run targeted verification for the packaged inventory and install surface, including `pixi run houmao-mgr system-skills list` and any relevant tests covering system-skill catalog expansion.
- [x] 3.2 Review the new skill and docs for routing accuracy so all neighboring references use the current renamed skill names and the documented project-aware behavior matches the live `houmao-mgr project` surface.
