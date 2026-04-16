## ADDED Requirements

### Requirement: Shared system-skill removal removes all current catalog-known projections
The system SHALL provide a shared removal contract for deleting Houmao-owned system-skill projections from one target tool home.

The removal contract SHALL load the packaged current-system-skill catalog and target every current skill name in catalog order.

For each current catalog-known skill, the removal contract SHALL compute the current tool-native destination path for the selected tool:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Copilot: `skills/<houmao-skill>/`
- Gemini: `.gemini/skills/<houmao-skill>/`

When a computed target path exists as a directory, file, or symlink, the removal contract SHALL remove that exact path.

When a computed target path is missing, the removal contract SHALL record that path as absent and SHALL NOT fail.

The removal contract SHALL NOT create the target home, parent skill roots, or any missing skill path.

The removal contract SHALL NOT remove parent skill roots, unrelated tool-home content, unrecognized `houmao-*` paths, legacy family-namespaced paths, or obsolete `.houmao/system-skills/install-state.json` files.

The removal contract SHALL return enough structured information for callers to report removed skill names, removed projected relative dirs, absent skill names, and absent projected relative dirs.

#### Scenario: Shared removal deletes copied and symlink projections
- **WHEN** the shared removal contract runs for a Codex home
- **AND WHEN** that home contains current catalog-known Houmao skills under `skills/` as copied directories, symlinks, or files
- **THEN** those exact current skill paths are removed
- **AND THEN** the removal result reports them as removed

#### Scenario: Shared removal preserves unrelated and legacy paths
- **WHEN** the shared removal contract runs for a target home
- **AND WHEN** that home contains a custom user skill, a parent `skills/` root, a legacy family-namespaced Houmao path, and an obsolete install-state file
- **THEN** those paths remain in place
- **AND THEN** only exact current catalog-known Houmao skill projection paths are removed

#### Scenario: Shared removal is a no-op for a missing home
- **WHEN** the shared removal contract runs for a target home path that does not exist
- **THEN** it does not create that home path
- **AND THEN** it reports every current catalog-known Houmao skill projection path for that tool as absent

#### Scenario: Shared removal targets Gemini's `.gemini/skills` projection root
- **WHEN** the shared removal contract runs for a Gemini home
- **THEN** it targets current Houmao-owned skill paths under `.gemini/skills/`
- **AND THEN** it does not target `.agents/skills/` as the primary Houmao-owned system-skill removal root
