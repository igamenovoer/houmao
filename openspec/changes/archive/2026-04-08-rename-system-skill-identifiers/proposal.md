## Why

The current packaged system-skill inventory still mixes two naming schemes. Four public skills use the older `houmao-manage-*` pattern while nearby skills already use the cleaner `houmao-agent-*` and `*-mgr` families, which makes the catalog, cross-skill routing text, and operator-facing docs harder to scan than they need to be.

These names are now baked into packaged asset paths, installer state, system-skills CLI output, tests, and current docs/specs, so a rename needs to be handled as one coordinated change instead of ad hoc directory moves.

## What Changes

- **BREAKING** Rename the packaged Houmao-owned system skill `houmao-manage-agent-definition` to `houmao-agent-definition`.
- **BREAKING** Rename the packaged Houmao-owned system skill `houmao-manage-agent-instance` to `houmao-agent-instance`.
- **BREAKING** Rename the packaged Houmao-owned system skill `houmao-manage-credentials` to `houmao-credential-mgr`.
- **BREAKING** Rename the packaged Houmao-owned system skill `houmao-manage-specialist` to `houmao-specialist-mgr`.
- Update the packaged catalog, installer migration rules, and `houmao-mgr system-skills` list/install/status reporting so the new names are the only current public skill identifiers.
- Update packaged skill content, action-page cross references, and agent metadata so routing guidance points at the renamed skills consistently.
- Update current user-facing docs and current OpenSpec specs to describe the renamed packaged skills as the active system-skill surface.
- Keep the underlying `houmao-mgr` command families, skill scopes, named sets, and managed-home versus CLI-default install behavior unchanged apart from the public skill identifiers and owned-path migration.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-system-skill-installation`: rename the current packaged catalog inventory and install-state migration rules to project the four renamed skills and retire previously owned paths for the old names.
- `houmao-mgr-system-skills-cli`: update list/install/status reporting and explicit skill selection to surface the renamed public skill identifiers.
- `houmao-create-specialist-skill`: replace the current packaged specialist-management skill identifier with `houmao-specialist-mgr` while preserving the existing easy-workflow scope and handoff to the lifecycle skill.
- `houmao-create-specialist-credential-sources`: move the specialist create-action credential-source rules under the renamed `houmao-specialist-mgr` skill name.
- `houmao-manage-credentials-skill`: rename the packaged credential-management contract from `houmao-manage-credentials` to `houmao-credential-mgr`.
- `houmao-manage-agent-definition-skill`: rename the packaged low-level definition-management contract from `houmao-manage-agent-definition` to `houmao-agent-definition`.
- `houmao-manage-agent-instance-skill`: rename the packaged lifecycle contract from `houmao-manage-agent-instance` to `houmao-agent-instance` and update its cross-skill relationship with the renamed specialist skill.
- `docs-readme-system-skills`: update the README system-skills inventory, install examples, and default-install explanation to use the renamed public skill identifiers.
- `docs-cli-reference`: update `docs/reference/cli/system-skills.md` to document the renamed skill inventory and the revised cross-skill naming consistently.
- `docs-system-skills-overview-guide`: update the getting-started system-skills overview to narrate the renamed skill inventory and its unchanged boundaries.

## Impact

- Affected code under `src/houmao/agents/assets/system_skills/`, especially the four renamed packaged skill trees, their action pages, and `agents/openai.yaml` metadata.
- Affected installer and reporting logic in `src/houmao/agents/system_skills.py`, `src/houmao/srv_ctrl/commands/system_skills.py`, and the focused tests that assert current skill names and projected paths.
- Affected user-facing docs in `README.md`, `docs/getting-started/system-skills-overview.md`, and `docs/reference/cli/system-skills.md`.
- Affected current OpenSpec requirements that name the active packaged skills; archived change history remains historical and is not rewritten by this change.
- Affected installed tool homes: Houmao-owned installations need owned-path migration from the old skill directories to the renamed directories on the next reinstall or auto-install.
