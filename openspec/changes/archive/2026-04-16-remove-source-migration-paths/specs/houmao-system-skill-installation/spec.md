## MODIFIED Requirements

### Requirement: Shared installer records Houmao-owned install state and preserves unrelated content
The shared installer SHALL record Houmao-owned install state under the target home and SHALL use current-schema install state to make repeated installation idempotent.

For each recorded installed skill, the install state SHALL record:

- the current skill name,
- the packaged asset subpath,
- the owned projected relative directory inside the tool home,
- the recorded projection mode,
- the recorded content digest.

When the current projection mode for one selected skill differs from a previously recorded current-schema Houmao-owned mode for that same skill, reinstall SHALL replace the previously owned in-home path with the newly requested projection mode and SHALL update install state to record only the current mode for that skill.

The installer SHALL preserve unrelated user-authored skill content in the target home.

If a required projected path collides with content that is not recorded as current-schema Houmao-owned install state, the installer SHALL fail explicitly rather than overwriting that content silently.

If Houmao encounters an old install-state record version, an old family-namespaced Houmao-owned skill path, or a previously renamed/superseded skill record, it SHALL reject that old install state or leave it outside current ownership instead of migrating it into the current install-state model.

#### Scenario: Reinstalling the same current skill set keeps the flat owned result stable
- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once using the same projection mode
- **THEN** the installer reuses current-schema Houmao-owned install state to keep the projected result consistent
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees or duplicate Houmao-owned symlink entries

#### Scenario: Reinstall switches one selected skill from copied projection to symlink projection
- **WHEN** a target tool home already records one selected current Houmao-owned skill as a copied projection in current-schema install state
- **AND WHEN** the operator reinstalls that same skill into the same owned tool-native path using symlink projection
- **THEN** the installer replaces the previously owned copied path with the requested symlink entry
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the current symlink projection mode for that skill

#### Scenario: Non-owned collision fails closed
- **WHEN** the shared installer needs to project a current Houmao-owned skill path into a target home
- **AND WHEN** that projected path is already occupied by content not recorded as current-schema Houmao-owned install state
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently overwrite the non-owned content

#### Scenario: Old copy-only install-state record is unsupported
- **WHEN** Houmao reads a previously recorded Houmao-owned install-state record that predates explicit projection-mode tracking
- **THEN** the installer rejects that old install-state shape explicitly
- **AND THEN** it does not infer copied projection mode as a migration fallback

#### Scenario: Old family-namespaced paths are not migrated
- **WHEN** a target tool home contains old Houmao-owned paths such as `skills/mailbox/<houmao-skill>/` or `skills/project/<houmao-skill>/`
- **AND WHEN** the current installer projects that skill into the current flat top-level tool-native path
- **THEN** the installer does not treat those old paths as migration inputs for current install state
- **AND THEN** the operator must clear old owned content or use a clean target home if those paths need removal

#### Scenario: Renamed skill records are not migrated
- **WHEN** a target tool home records old Houmao-owned install state for a superseded skill name such as `houmao-create-specialist`
- **AND WHEN** the current packaged catalog selects the current replacement skill name
- **THEN** the installer does not migrate the superseded record into the current skill name
- **AND THEN** the operator must reinstall current system skills using current install state
