## MODIFIED Requirements

### Requirement: Shared installer projects selected current Houmao-owned skills into target tool homes
The system SHALL install only the selected current Houmao-owned skills into a target tool home through one shared installer contract used by both explicit operator installation and Houmao-managed runtime installation.

For the current skill set, the visible projected paths SHALL remain tool-native:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Gemini: `.gemini/skills/<houmao-skill>/`

The shared installer SHALL support these projection modes:

- `copy` for copied packaged skill trees,
- `symlink` for directory symlinks whose in-home path is the tool-native skill path.

For explicit operator installation, the shared installer SHALL default to `copy` projection mode unless the operator explicitly requests `symlink`.

For Houmao-managed runtime installation, the shared installer SHALL continue to use `copy` projection mode in this change.

When explicit operator installation requests `symlink` mode, the shared installer SHALL create one directory symlink per selected skill at the tool-native destination path and SHALL use the absolute filesystem path of the packaged skill asset directory as the symlink target.

If the packaged skill asset directory cannot be addressed as a stable real filesystem directory path, explicit `symlink` installation SHALL fail explicitly and SHALL NOT silently fall back to copied projection.

The shared installer SHALL NOT require a project-local copied skill mirror or worktree-local `SKILL.md` path for ordinary use of those installed skills.

#### Scenario: Explicit copy installation projects one selected current skill into a Codex home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Codex home without requesting symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as copied content
- **AND THEN** it does not require a copied project-local skill mirror for ordinary use of that installed skill

#### Scenario: Explicit symlink installation projects one selected current skill into a Codex home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Codex home and explicitly requests symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as a directory symlink
- **AND THEN** the symlink target is the absolute filesystem path of the packaged skill asset directory

#### Scenario: Managed home installation preserves the current Gemini skill root with copied projection
- **WHEN** Houmao installs selected current Houmao-owned skills into a managed Gemini home
- **THEN** the installer projects those skills under `.gemini/skills/`
- **AND THEN** it uses copied projection rather than symlink projection in this change
- **AND THEN** it does not require `.agents/skills` as the primary visible projection root for those installed skills

#### Scenario: Explicit symlink installation fails when the packaged skill root is not filesystem-backed
- **WHEN** an operator explicitly requests symlink installation for one selected current Houmao-owned skill
- **AND WHEN** the packaged skill asset directory does not have a stable real filesystem directory path
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently replace that request with copied projection
