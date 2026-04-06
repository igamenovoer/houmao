## Why

Houmao currently separates reusable specialist authoring from runtime-managed agent lifecycle, but it does not provide one Houmao-owned skill focused on creating and managing agent instances from predefined sources. Operators need a narrower lifecycle skill that covers launch, join, stop, and cleanup without pulling mailbox management or specialist CRUD into the same surface.

## What Changes

- Add a new packaged Houmao-owned system skill named `houmao-manage-agent-instance`.
- Scope that skill to managed-agent instance lifecycle only:
  - launch one predefined agent from `houmao-mgr agents launch`
  - launch one specialist-backed instance from `houmao-mgr project easy instance launch`
  - join one existing session through `houmao-mgr agents join`
  - list live managed agents through `houmao-mgr agents list`
  - stop one managed agent through `houmao-mgr agents stop`
  - clean stopped-session artifacts through `houmao-mgr agents cleanup session|logs`
- Keep mailbox management, mailbox cleanup, gateway control, prompt submission, and specialist CRUD out of scope for the new skill.
- Add the new packaged skill to the system-skill catalog and default CLI install selection so CLI-default installs expose both specialist management and agent-instance lifecycle guidance together.
- Update CLI reference docs to describe the new packaged skill and its boundary relative to `houmao-manage-specialist`.

## Capabilities

### New Capabilities
- `houmao-manage-agent-instance-skill`: Packaged Houmao-owned skill that routes managed-agent instance lifecycle actions across direct launch, specialist-backed launch, join, list, stop, and cleanup.

### Modified Capabilities
- `houmao-system-skill-installation`: The packaged system-skill catalog and CLI-default selection change to include `houmao-manage-agent-instance` alongside the existing specialist-management packaged skill.
- `houmao-mgr-system-skills-cli`: `system-skills list|install|status` reflect the new packaged skill and the updated CLI-default selection outcome.
- `docs-cli-reference`: CLI reference docs describe the new packaged agent-instance skill, its lifecycle-only boundary, and how it relates to the existing packaged specialist-management skill.

## Impact

- Affected code: `src/houmao/agents/assets/system_skills/`, `src/houmao/agents/system_skills.py`, `src/houmao/agents/assets/system_skills/catalog.toml`
- Affected docs: `docs/reference/cli/system-skills.md` and related CLI reference pages
- Affected tests: system-skill catalog/installer tests and `system-skills` CLI tests
