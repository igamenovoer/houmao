## Why

The packaged Houmao system skill `houmao-create-specialist` is now too narrow for the actual `houmao-mgr project easy specialist` surface. The CLI already exposes `create`, `list`, `get`, and `remove`, but the installed skill only teaches creation, which fragments the specialist-management workflow and leaves the packaged skill name out of sync with the broader operator task.

## What Changes

- **BREAKING** Rename the packaged Houmao-owned system skill from `houmao-create-specialist` to `houmao-manage-specialist`.
- Expand that packaged skill to cover `houmao-mgr project easy specialist create|list|get|remove`, while keeping `project easy instance launch` explicitly out of scope.
- Restructure the skill tree so the top-level `SKILL.md` serves as an index/router and action-specific guidance lives in separate local action documents.
- Keep credential discovery, tool-specific lookup guidance, and vendor-auth import rules attached only to the create action inside the broader management skill.
- Update packaged catalog entries, installer ownership tracking, and migration behavior so previously owned `houmao-create-specialist` installs move cleanly to `houmao-manage-specialist`.
- Update CLI and system-skill reference docs to describe the renamed packaged skill and its broader specialist-management scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-create-specialist-skill`: Replace the create-only packaged skill contract with the broader `houmao-manage-specialist` skill contract, including create, list, get, and remove routing.
- `houmao-create-specialist-credential-sources`: Preserve create-action credential-source modes and tool-specific lookup guidance under the renamed specialist-management skill.
- `houmao-system-skill-installation`: Change packaged inventory and owned install migration to project `houmao-manage-specialist` and retire previously owned `houmao-create-specialist` paths.
- `houmao-mgr-system-skills-cli`: Update the reported Houmao-owned system-skill inventory and install/status results to use the renamed packaged skill.
- `docs-cli-reference`: Update CLI reference coverage so packaged skill inventory and system-skill reference content describe `houmao-manage-specialist` instead of `houmao-create-specialist`.

## Impact

- Affected code: `src/houmao/agents/assets/system_skills/`, `src/houmao/agents/system_skills.py`, `src/houmao/srv_ctrl/commands/system_skills.py`, and related tests.
- Affected docs: `docs/reference/cli/system-skills.md`, `docs/reference/cli/houmao-mgr.md`, and any skill-specific references that name the packaged specialist-authoring skill.
- Affected installed homes: existing Houmao-owned tool homes need owned-path migration from `skills/houmao-create-specialist/` or `.agents/skills/houmao-create-specialist/` to the new `houmao-manage-specialist` path.
