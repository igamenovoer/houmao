## MODIFIED Requirements

### Requirement: Shared installer projects selected current Houmao-owned skills into target tool homes

The system SHALL install only the selected current Houmao-owned skills into a target tool home through one shared installer contract used by both explicit operator installation and Houmao-managed runtime installation.

For the current skill set, the visible projected paths SHALL remain tool-native:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Gemini: `.agents/skills/<houmao-skill>/`

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
- **THEN** the installer projects those skills under `.agents/skills/`
- **AND THEN** it uses copied projection rather than symlink projection in this change
- **AND THEN** it does not require `.gemini/skills` as the primary visible projection root for those installed skills

#### Scenario: Explicit symlink installation fails when the packaged skill root is not filesystem-backed

- **WHEN** an operator explicitly requests symlink installation for one selected current Houmao-owned skill
- **AND WHEN** the packaged skill asset directory does not have a stable real filesystem directory path
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently replace that request with copied projection

### Requirement: Shared installer records Houmao-owned install state and preserves unrelated content

The shared installer SHALL record Houmao-owned install state under the target home and SHALL use that state to make repeated installation idempotent.

For each recorded installed skill, the install state SHALL record:

- the current skill name,
- the packaged asset subpath,
- the owned projected relative directory inside the tool home,
- the recorded projection mode,
- the recorded content digest.

When the current projected path for one selected skill differs from a previously recorded Houmao-owned path for that same skill, reinstall SHALL remove the previously owned path before or during projection of the new path and SHALL update install state to record only the current owned path for that skill.

When the current projection mode for one selected skill differs from a previously recorded Houmao-owned mode for that same skill, reinstall SHALL replace the previously owned in-home path with the newly requested projection mode and SHALL update install state to record only the current mode for that skill.

When the current packaged skill name supersedes a previously recorded Houmao-owned skill name for the same maintained workflow, reinstall or auto-install SHALL remove the previously owned path for the superseded skill and SHALL update install state to keep only the current renamed skill record.

The installer SHALL preserve unrelated user-authored skill content in the target home.

If a required projected path collides with content that is not recorded as Houmao-owned install state, the installer SHALL fail explicitly rather than overwriting that content silently.

If Houmao encounters a previously recorded copy-only install-state record from before projection mode was tracked explicitly, it SHALL continue to treat that owned record as a copied projection during status and reinstall.

#### Scenario: Reinstalling the same current skill set keeps the flat owned result stable

- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once using the same projection mode
- **THEN** the installer reuses Houmao-owned install state to keep the projected result consistent
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees or duplicate Houmao-owned symlink entries

#### Scenario: Reinstall switches one selected skill from copied projection to symlink projection

- **WHEN** a target tool home already records one selected current Houmao-owned skill as a copied projection
- **AND WHEN** the operator reinstalls that same skill into the same owned tool-native path using symlink projection
- **THEN** the installer replaces the previously owned copied path with the requested symlink entry
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the current symlink projection mode for that skill

#### Scenario: Reinstall migrates a previously owned family-namespaced path

- **WHEN** a target tool home already records a Houmao-owned path such as `skills/mailbox/<houmao-skill>/` or `skills/project/<houmao-skill>/` for one selected skill
- **AND WHEN** the current installer now projects that same skill into the flat top-level tool-native path
- **THEN** reinstall removes the previously owned family-namespaced path before or during projection of the new path
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the current flat owned path for that skill
- **AND THEN** the target home does not retain stale Houmao-owned namespace directories for that migrated skill

#### Scenario: Reinstall migrates the renamed specialist-management skill

- **WHEN** a target tool home already records Houmao-owned install state for `houmao-create-specialist`
- **AND WHEN** the current packaged catalog now selects `houmao-manage-specialist`
- **THEN** reinstall or auto-install removes the previously owned `houmao-create-specialist` projected directory before or during projection of `houmao-manage-specialist`
- **AND THEN** the recorded Houmao-owned install state is updated to keep only `houmao-manage-specialist`
- **AND THEN** the target home does not retain the stale owned `houmao-create-specialist` directory alongside the renamed skill

#### Scenario: Non-owned collision fails closed

- **WHEN** the shared installer needs to project a current Houmao-owned skill path into a target home
- **AND WHEN** that projected path is already occupied by content not recorded as Houmao-owned install state
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently overwrite the non-owned content

#### Scenario: Upgrade reads a previously recorded copy-only install-state record

- **WHEN** Houmao reads a previously recorded Houmao-owned install-state record that predates explicit projection-mode tracking
- **THEN** the system treats that record as a copied projection for status and reinstall purposes
- **AND THEN** the existing owned copied skill path remains manageable by the shared installer
