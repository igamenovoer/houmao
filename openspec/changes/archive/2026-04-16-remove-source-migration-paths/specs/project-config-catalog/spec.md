## ADDED Requirements

### Requirement: Project-local catalog incompatibilities are hard-reset only before 1.0
Project-local catalog initialization SHALL create the current catalog schema when the project overlay has no catalog yet.

When a project overlay already contains a catalog, initialization SHALL validate that the catalog uses the current supported schema version and required current-format invariants before continuing.

When an existing catalog is missing required current-format metadata, reports an unsupported schema version, or exposes an obsolete current-table shape, Houmao SHALL fail explicitly and direct the operator to recreate or reinitialize the project overlay. Houmao SHALL NOT mutate that existing catalog through an in-place compatibility migration.

#### Scenario: Fresh project creates the current catalog schema
- **WHEN** an operator creates a Houmao project from scratch
- **THEN** Houmao initializes the project-local catalog with the current schema
- **AND THEN** the project can create mailbox configuration, specialists, launch profiles, and managed agents without running old-format migration code

#### Scenario: Unsupported existing catalog fails with recreate guidance
- **WHEN** Houmao opens a project overlay whose existing catalog reports an unsupported schema version
- **THEN** catalog initialization fails before mutating the catalog
- **AND THEN** the diagnostic directs the operator to recreate or reinitialize the project overlay instead of promising an in-place migration

#### Scenario: Obsolete table shape is not repaired in place
- **WHEN** an existing project catalog reports the current schema version but still has an obsolete table constraint or removed column
- **THEN** Houmao treats the catalog as incompatible current-version state
- **AND THEN** Houmao fails explicitly instead of rebuilding catalog tables in place

## MODIFIED Requirements

### Requirement: Project-local catalog surfaces stable advanced inspection semantics

The project-local catalog SHALL expose a stable advanced inspection surface suitable for SQL-based operator inspection for catalogs created by the current supported Houmao version.

At minimum, that surface SHALL provide:

- schema versioning,
- foreign-key-backed relationship integrity,
- stable read-oriented inspection tables or views for core project-local objects.

If advanced users manipulate project-local catalog state through SQL tools, the system SHALL define that surface intentionally rather than relying on undocumented path reconstruction behavior.

Schema versioning SHALL be used to reject unsupported persisted catalog formats. It SHALL NOT imply that Houmao maintains in-place upgrade paths for older pre-1.0 catalog versions.

#### Scenario: Advanced operator inspects project-local semantic objects through SQL
- **WHEN** an advanced operator opens a current project-local SQLite catalog with SQL tooling
- **THEN** they can inspect stable semantic objects such as specialists, roles, recipes, launch profiles, and content references directly from the catalog
- **AND THEN** the inspection surface does not require reconstructing relationships from directory nesting under `.houmao/agents/`

#### Scenario: Schema version mismatch fails instead of migrating
- **WHEN** Houmao opens an existing project-local SQLite catalog whose stored schema version is not the current supported version
- **THEN** Houmao rejects that catalog explicitly
- **AND THEN** it does not attempt to upgrade the catalog schema in place

## REMOVED Requirements

### Requirement: Legacy project-local tree-backed overlays can be imported into the catalog
**Reason**: Houmao is pre-1.0 and no longer maintains source-level migration paths from older project-local layouts into the current SQLite catalog model.

**Migration**: Recreate the Houmao project overlay and define specialists, launch profiles, auth profiles, mailbox configuration, and agents through the current catalog-backed project commands.
