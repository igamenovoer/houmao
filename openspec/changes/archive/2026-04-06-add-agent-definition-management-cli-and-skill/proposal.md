## Why

Houmao's current low-level project-local agent-definition surface already supports the edit operations we need:

- role prompt mutation through `houmao-mgr project agents roles set`
- named preset mutation through `houmao-mgr project agents presets set`
- auth-bundle content mutation through `houmao-mgr project agents tools <tool> auth set`

The remaining gap is different from what this change originally described. The repository still lacks a packaged Houmao-owned `houmao-manage-agent-definition` skill aligned with the current CLI shape, and `project agents roles get` still reports only prompt paths rather than optional prompt content. That means a truthful low-level definition-management skill cannot yet cover full inspection and routing through the maintained current command surfaces.

## What Changes

- Add opt-in prompt inspection to `houmao-mgr project agents roles get` through `--include-prompt`.
- Add a packaged Houmao-owned `houmao-manage-agent-definition` skill that routes low-level definition work through the current maintained surfaces:
  - `houmao-mgr project agents roles ...`
  - `houmao-mgr project agents presets ...`
- Keep auth-bundle content mutation out of that new skill and on the existing `houmao-manage-credentials` workflow backed by `houmao-mgr project agents tools <tool> auth ...`.
- Add `houmao-manage-agent-definition` to the packaged `user-control` system-skill set and update `houmao-mgr system-skills` reporting for the expanded inventory.

## Capabilities

### New Capabilities

- `houmao-manage-agent-definition-skill`: Packaged skill guidance for creating, listing, inspecting, updating, and removing low-level project-local roles and named presets through the supported current `houmao-mgr` command surfaces.

### Modified Capabilities

- `houmao-mgr-project-agents-roles`: Add opt-in prompt-content inspection to role lookup.
- `houmao-system-skill-installation`: Expand the packaged `user-control` set to include the new definition-management skill.
- `houmao-mgr-system-skills-cli`: Surface the new packaged skill and updated `user-control` membership in `list`, `install`, and `status` flows.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/system_skills.py`, `src/houmao/agents/assets/system_skills/catalog.toml`, and a new packaged skill asset tree under `src/houmao/agents/assets/system_skills/`.
- Affected tests: project command coverage for `project agents roles get --include-prompt` and system-skill inventory / CLI coverage.
- Affected docs: `houmao-mgr` CLI reference and system-skills reference for the current low-level role/preset/auth boundary and the new packaged skill surface.
