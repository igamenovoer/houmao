## Why

Houmao still ties auth-bundle identity to human-facing names and directory basenames, which makes rename expensive and leaks storage layout into semantic relationships. Now that project-local semantic state is centered on the SQLite catalog, auth identity should follow the same model: stable opaque internal identity in the catalog, mutable display names for operators.

## What Changes

- **BREAKING** Make auth profiles catalog-owned semantic objects whose stable identity is an opaque bundle reference rather than the display name.
- **BREAKING** Store auth content under opaque bundle-reference paths instead of name-derived paths in both managed content storage and the compatibility projection tree.
- Add `houmao-mgr project agents tools <tool> auth rename` for renaming an existing auth profile without moving its underlying identity.
- **BREAKING** Make `project agents tools <tool> auth list|get|add|set|remove|rename` resolve auth profiles through the catalog instead of scanning `.houmao/agents/tools/<tool>/auth/` as the source of truth.
- **BREAKING** Replace text name references for stored auth relationships, especially launch-profile auth overrides, with catalog-backed auth-profile references.
- **BREAKING** Remove specialist-owned auth-name authority and derive specialist auth display names from the referenced auth profile instead of persisting the display name as a second identity source.
- Update skill guidance and project-easy authoring flows to treat auth display names as user-facing labels only, while opaque refs own storage and projection paths.

## Capabilities

### New Capabilities
- `auth-profile-rename`: Rename one project-local auth profile without changing the underlying auth content identity or requiring storage-path moves.

### Modified Capabilities
- `project-config-catalog`: Auth profiles and auth relationships become catalog-owned identities backed by opaque bundle refs rather than name-shaped storage keys.
- `houmao-mgr-project-agent-tools`: Tool auth CRUD becomes catalog-backed and adds an explicit `auth rename` surface.
- `houmao-mgr-project-agents-launch-profiles`: Stored launch-profile auth overrides resolve through auth-profile identity rather than persisting display-name text as the relationship key.
- `houmao-mgr-project-easy-cli`: Easy specialist and easy-profile flows stop treating auth display names or auth paths as authoritative identity.
- `houmao-manage-credentials-skill`: The packaged auth-management skill routes rename and treats direct auth-path editing or name-derived storage assumptions as unsupported.
- `houmao-create-specialist-skill`: The packaged specialist-management skill treats default credential names as display-name defaults only and does not imply name-shaped storage identity.

## Impact

- Affected code: `src/houmao/project/catalog.py`, `src/houmao/srv_ctrl/commands/project.py`, project-aware auth materialization, launch-profile storage, easy-specialist storage, and packaged system-skill assets under `src/houmao/agents/assets/system_skills/`.
- Affected artifacts: project-local SQLite schema and views, managed content layout under `.houmao/content/auth/`, compatibility projection paths under `.houmao/agents/tools/<tool>/auth/`, and user-facing auth-management command help/output.
- Affected workflows: project-local auth CRUD, auth rename, easy specialist creation, launch-profile auth overrides, and skill-driven credential-management guidance.
