## Why

Houmao now has a supported low-level auth-bundle CLI surface, but the packaged system-skill set does not yet provide a matching skill for agents to list, inspect, add, update, or remove those credentials safely. At the same time, the current `project-easy` set name no longer fits the intended install scope once credential management joins specialist authoring in the same packaged family.

## What Changes

- Add a packaged `houmao-manage-credentials` system skill that routes agents to `houmao-mgr project agents tools <tool> auth list|get|add|set|remove` with launcher resolution, per-action guidance, and safe auth inspection behavior.
- Define the new skill as project-local auth-bundle management for the supported Claude, Codex, and Gemini tool families rather than as generic secret management or runtime mailbox credential handling.
- Add `houmao-manage-credentials` to the current non-mailbox packaged skill set that installs into user-controlled agents.
- **BREAKING** Rename the packaged system-skill set currently called `project-easy` to `user-control`, and update packaged catalog, installer defaults, CLI reporting, and spec language to use the new set name.
- Keep the existing packaged skill names `houmao-manage-specialist` and `houmao-manage-credentials`; only the named set changes.

## Capabilities

### New Capabilities
- `houmao-manage-credentials-skill`: Packaged low-level auth-bundle management guidance for list, get, add, set, and remove actions across Claude, Codex, and Gemini.

### Modified Capabilities
- `houmao-system-skill-installation`: Rename the `project-easy` named set to `user-control`, add `houmao-manage-credentials` to that set, and update fixed auto-install selections to reference the renamed set.
- `houmao-system-skill-families`: Update logical-group language and default-selection scenarios so the non-mailbox user-controlled skill family uses `user-control` instead of `project-easy`.
- `houmao-mgr-system-skills-cli`: Update `system-skills list|install|status` reporting and default-selection language to surface the renamed `user-control` set and the new `houmao-manage-credentials` skill.

## Impact

- Affected code: packaged system-skill assets under `src/houmao/agents/assets/system_skills/`, the packaged catalog and installer helpers in `src/houmao/agents/system_skills.py`, and any CLI reporting code that prints named set membership.
- Affected tests: system-skill catalog, install-state, and CLI reporting coverage under `tests/unit/agents/` and `tests/unit/srv_ctrl/`.
- Affected docs/specs: OpenSpec delta specs for system-skill installation/families/CLI, plus system-skill and CLI reference docs that still refer to the `project-easy` set name.
