## ADDED Requirements

### Requirement: Shared installer overwrites selected current skill projections without install state
The shared installer SHALL NOT create, read, validate, or update Houmao-owned install-state metadata inside the target tool home when installing current system skills.

For each selected current Houmao-owned skill, the installer SHALL compute the exact current tool-native projected destination path for that skill.

If that selected destination path already exists as a directory, file, or symlink, the installer SHALL remove it before projecting the packaged skill.

The installer SHALL then project the selected packaged skill into that destination using the requested projection mode:

- `copy` SHALL materialize the packaged skill tree as copied content,
- `symlink` SHALL create a directory symlink to the packaged skill asset root.

The installer SHALL limit destructive replacement to selected current skill destination paths. The installer SHALL NOT remove unselected skill directories, parent skill roots, legacy family-namespaced paths, unrelated tool-home content, or stale install-state files.

If explicit symlink projection is requested and the packaged skill asset directory cannot be addressed as a stable real filesystem directory path, installation SHALL fail explicitly and SHALL NOT silently fall back to copied projection.

#### Scenario: Reinstalling copied skills refreshes selected destinations without state
- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once using copied projection
- **THEN** the installer replaces each selected skill's exact destination path with freshly copied packaged content
- **AND THEN** the target home does not require `.houmao/system-skills/install-state.json` for idempotent reinstall
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees

#### Scenario: Reinstall switches one selected skill from copied projection to symlink projection
- **WHEN** a target tool home already contains one selected current Houmao-owned skill as a copied directory
- **AND WHEN** the operator reinstalls that same skill into the same current tool-native path using symlink projection
- **THEN** the installer removes the copied directory
- **AND THEN** the installer creates the requested symlink entry at that same destination
- **AND THEN** no install-state metadata is written into the target home

#### Scenario: Existing selected Houmao skill path is overwritten without ownership proof
- **WHEN** the shared installer needs to project a selected current Houmao-owned skill path into a target home
- **AND WHEN** that projected path is already occupied by existing content
- **THEN** the installer removes the existing selected path without requiring current-schema Houmao-owned install-state proof
- **AND THEN** the installer projects the selected packaged skill into that path

#### Scenario: Unselected and unrelated content is preserved
- **WHEN** a target home contains an unselected skill directory, a legacy family-namespaced skill path, and an obsolete `.houmao/system-skills/install-state.json`
- **AND WHEN** Houmao installs a different selected current Houmao-owned skill
- **THEN** the installer replaces only the selected current skill destination path when needed
- **AND THEN** the unselected skill directory, legacy family-namespaced path, and obsolete install-state file remain untouched

## REMOVED Requirements

### Requirement: Shared installer records Houmao-owned install state and preserves unrelated content
**Reason**: The current installer contract is being simplified before 1.0. Selected current Houmao-owned skill paths are now explicit overwrite targets, so persisted install-state ownership proof and non-owned collision failures are unnecessary complexity.

**Migration**: Existing tool homes do not require migration. Future installs ignore old `.houmao/system-skills/install-state.json` files and replace only the selected current skill destination paths.
