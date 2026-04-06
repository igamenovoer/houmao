## Why

Houmao's low-level project-local agent-definition surface can create, list, inspect, and remove roles and presets, but it cannot update a role prompt or preset fields in place through `houmao-mgr`. That leaves a gap between the supported CLI and the packaged skill surface we want to install into user-controlled agents, because a truthful `houmao-manage-agent-definition` skill cannot promise definition editing while the CLI still requires ad hoc file edits.

## What Changes

- Add low-level update commands for project-local agent definitions: `houmao-mgr project agents roles set` and `houmao-mgr project agents roles presets set`.
- Extend role inspection so agents can optionally inspect prompt content through `houmao-mgr` instead of only receiving a prompt path.
- Add a packaged Houmao-owned `houmao-manage-agent-definition` skill that routes low-level role and preset management through the supported `project agents roles ...` command surface.
- Add `houmao-manage-agent-definition` to the packaged `user-control` system-skill set and update `houmao-mgr system-skills` reporting for the expanded inventory.
- Keep the boundary between definition structure and credential contents explicit: changing which auth bundle a preset references belongs to the new definition-management surface, while mutating auth-bundle contents stays on `houmao-manage-credentials`.

## Capabilities

### New Capabilities
- `houmao-manage-agent-definition-skill`: Packaged skill guidance for creating, listing, inspecting, updating, and removing low-level project-local agent definitions through supported `houmao-mgr` role and preset commands.

### Modified Capabilities
- `houmao-mgr-project-agents-roles`: Add supported in-place update verbs and richer inspection for project-local role prompts and role presets.
- `houmao-system-skill-installation`: Expand the packaged `user-control` set to include the new definition-management skill.
- `houmao-mgr-system-skills-cli`: Surface the new packaged skill and updated `user-control` membership in `list`, `install`, and `status` flows.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/system_skills.py`, `src/houmao/agents/assets/system_skills/catalog.toml`, and a new packaged skill asset tree under `src/houmao/agents/assets/system_skills/`.
- Affected tests: project command coverage for `project agents roles ...` and system-skill inventory / CLI coverage.
- Affected docs: `houmao-mgr` CLI reference and system-skills reference for the expanded low-level authoring and packaged skill surface.
