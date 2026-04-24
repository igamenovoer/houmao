## ADDED Requirements

### Requirement: Destructive filesystem mutations stay within declared Houmao-owned lexical roots
Any Houmao workflow that deletes, replaces, or recursively rewrites filesystem artifacts SHALL perform that mutation against the lexical artifact path under one or more declared Houmao-owned roots.

The system SHALL NOT dereference the artifact path being mutated in order to choose the mutation target.

If the selected artifact path falls outside the declared owned roots, the system SHALL fail clearly before mutating the filesystem.

#### Scenario: Symlink-backed owned artifact is replaced without mutating its target
- **WHEN** Houmao selects one managed artifact path under a declared owned root for replacement
- **AND WHEN** that artifact path currently exists as a symlink to a directory outside the owned root
- **THEN** Houmao replaces or removes only the artifact path under the owned root
- **AND THEN** it does not delete or rewrite the symlink target directory

#### Scenario: External lexical path is rejected for destructive mutation
- **WHEN** a destructive helper is asked to mutate one lexical path outside its declared Houmao-owned roots
- **THEN** the operation fails clearly before mutating the filesystem

### Requirement: Caller-owned source paths are read-only by default
When a Houmao workflow accepts one caller-provided source file or directory for import, projection, migration, validation, or update, that source path SHALL be treated as read-only input unless the workflow explicitly declares ownership transfer.

Refresh, rollback, cleanup, or replacement of Houmao-managed artifacts SHALL NOT delete, move, rewrite, or partially consume the caller-provided source path.

#### Scenario: Managed refresh preserves caller-owned source directory
- **WHEN** an operator provides one source directory outside Houmao-managed space to a workflow that snapshots or links managed content
- **AND WHEN** Houmao later refreshes the corresponding managed artifact
- **THEN** the external source directory remains intact with its original content

#### Scenario: Failed managed update preserves caller-owned source file
- **WHEN** an operator provides one source file outside Houmao-managed space to a workflow that copies managed content
- **AND WHEN** the managed update fails after touching only Houmao-managed artifacts
- **THEN** the external source file remains intact
