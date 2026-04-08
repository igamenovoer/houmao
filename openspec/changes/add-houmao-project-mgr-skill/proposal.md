## Why

Houmao already exposes a real project lifecycle surface through `houmao-mgr project`, but the packaged system-skill inventory has no skill that explains project overlay creation, project-aware layout, launch-profile management, or project-scoped easy-instance inspection. That gap now matters because the renamed skill family is already live, and agents need one current packaged entrypoint that explains how project existence changes other Houmao commands.

## What Changes

- Add a new packaged system skill, `houmao-project-mgr`, under `src/houmao/agents/assets/system_skills/`.
- Define `houmao-project-mgr` as the project-level router for `houmao-mgr project init`, `houmao-mgr project status`, `project agents launch-profiles ...`, and `project easy instance list|get|stop`.
- Require the new skill to explain project overlay discovery, `.houmao/` layout, catalog versus compatibility-projection paths, and project-aware side effects on other command families such as `brains`, `agents`, `mailbox`, `server`, and runtime cleanup.
- Require the new skill to route neighboring concerns to the already-renamed packaged skills: `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, and `houmao-mailbox-mgr`.
- Add `houmao-project-mgr` to the packaged catalog and include it in the `user-control` set so managed launch/join installs and CLI-default installs surface it automatically.
- Update the `houmao-mgr system-skills` behavior/spec coverage so inventory, named-set reporting, install results, and status reporting reflect the expanded `user-control` set and current ten-skill packaged inventory.
- Update README, system-skills overview, and CLI reference requirements so docs describe `houmao-project-mgr`, the ten-skill inventory, the expanded `user-control` set, and the new renamed-skill routing boundaries.

## Capabilities

### New Capabilities

- `houmao-project-mgr-skill`: Packaged project-management system skill covering project overlay lifecycle, project layout/materialization, project-aware command effects, explicit launch-profile management, and project-scoped easy-instance inspection and stop routing.

### Modified Capabilities

- `houmao-system-skill-installation`: Expand the packaged catalog and `user-control` set to include `houmao-project-mgr`.
- `houmao-mgr-system-skills-cli`: Reflect `houmao-project-mgr` in `system-skills list|install|status`, including the expanded `user-control` and CLI-default selections.
- `docs-readme-system-skills`: Document `houmao-project-mgr` in the README system-skills subsection and update packaged-skill counts and default-install descriptions.
- `docs-system-skills-overview-guide`: Add `houmao-project-mgr` to the narrative system-skills guide and update the packaged inventory and named-set explanations.
- `docs-cli-reference`: Require `docs/reference/cli/system-skills.md` to document `houmao-project-mgr`, its routed `project` command families, and its boundaries versus the other renamed packaged skills.

## Impact

- Packaged system-skill assets under `src/houmao/agents/assets/system_skills/`, especially `catalog.toml` and the new `houmao-project-mgr/` tree.
- System-skill installation and reporting code that reads the packaged catalog and expands named sets.
- Operator-facing docs: `README.md`, `docs/getting-started/system-skills-overview.md`, and `docs/reference/cli/system-skills.md`.
- Managed homes and explicit external tool homes that auto-install or explicitly install the `user-control` set.
