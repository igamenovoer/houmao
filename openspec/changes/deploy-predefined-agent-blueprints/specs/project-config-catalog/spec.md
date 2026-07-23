## ADDED Requirements

### Requirement: Project catalog stores canonical agent deployment ownership and provenance

Project-local overlays SHALL store each applied agent blueprint deployment as a canonical SQLite catalog object.

Each deployment record SHALL contain:

- a stable deployment id and unique display name;
- blueprint id, blueprint version, source kind, source reference, and source digest;
- a managed normalized-input content reference and digest;
- foreign-key-backed ownership of one specialist and one launch profile;
- an output manifest that identifies deployment-owned registered skills, private-skill paths, managed content references, and last-applied digests;
- creation and last-application timestamps.

Project-local directory nesting or a standalone receipt file SHALL NOT replace the catalog as the source of deployment ownership and relationships.

#### Scenario: Applied deployment is inspectable in SQLite

- **WHEN** an operator applies one agent blueprint deployment
- **THEN** the project catalog records its blueprint provenance and owned specialist and profile relationships
- **AND THEN** advanced inspection can discover that ownership without reconstructing it from directory names

### Requirement: Deployment task inputs and private skills remain file-backed

Normalized deployment inputs and deployment-owned private skill trees SHALL remain file-backed beneath overlay-owned managed content roots.

Deployment-owned private skills SHALL use lexical paths under `.houmao/content/agent-deployments/<deployment-id>/skills/`. Specialist prompts, profile overlays, memo seeds, and registered skills SHALL continue to use their maintained content kinds and canonical managed locations.

The catalog SHALL reference these payloads and their digests. Catalog update and removal SHALL mutate only lexical overlay-owned artifact paths and SHALL NOT follow a symlink target.

#### Scenario: Private skill content is catalog-related but file-backed

- **WHEN** a deployment owns one generated profile-private skill
- **THEN** the complete skill directory exists under the deployment-owned managed content root
- **AND THEN** the catalog records the profile relationship, deployment ownership, and last-applied digest

### Requirement: Known deployment schema upgrade runs only through project migration

The catalog schema version that introduces agent blueprint deployment records SHALL have an explicit migration step from the immediately preceding supported catalog schema.

Ordinary project initialization, status, definition commands, and catalog materialization SHALL NOT apply that schema change implicitly. They SHALL reject the known preceding schema with guidance to run `houmao-mgr project migrate`.

Unknown or older unsupported catalog schemas SHALL continue to fail with recreate or restore guidance rather than receiving an inferred migration.

#### Scenario: Previous catalog requires explicit migration

- **WHEN** an existing project uses the immediately preceding catalog schema
- **AND WHEN** an operator runs an ordinary current project-definition command
- **THEN** Houmao rejects the catalog with `project migrate` guidance
- **AND THEN** it does not add deployment tables as an ordinary command side effect

#### Scenario: Project migrate adds deployment storage

- **WHEN** an operator runs `houmao-mgr project migrate` for the known immediately preceding schema
- **THEN** the migration preserves existing specialists, profiles, credentials, and skills
- **AND THEN** it adds the current empty deployment storage and advances the catalog schema version

## MODIFIED Requirements

### Requirement: Project-local catalog incompatibilities are hard-reset only before 1.0
Project-local catalog initialization SHALL create the current catalog schema when the project overlay has no catalog yet.

When a project overlay already contains a catalog, initialization SHALL validate that the catalog uses the current supported schema version and required current-format invariants before continuing.

For a specifically supported post-1.0 source schema, Houmao MAY provide an explicit, centralized `houmao-mgr project migrate` step that preserves catalog semantics while advancing to the current schema. Ordinary catalog initialization and project commands SHALL NOT run that migration implicitly.

When an existing catalog is missing required current-format metadata, reports an unsupported schema version for which no explicit migration exists, or exposes an obsolete current-table shape, Houmao SHALL fail explicitly and direct the operator to restore, recreate, or reinitialize the project overlay. Houmao SHALL NOT guess an in-place compatibility migration.

#### Scenario: Fresh project creates the current catalog schema
- **WHEN** an operator creates a Houmao project from scratch
- **THEN** Houmao initializes the project-local catalog with the current schema
- **AND THEN** the project can create mailbox configuration, specialists, launch profiles, agent blueprint deployments, and managed agents without running old-format migration code

#### Scenario: Supported preceding schema requires explicit migration
- **WHEN** Houmao opens a project overlay whose catalog reports a specifically supported preceding schema version
- **THEN** ordinary catalog initialization fails before mutating the catalog
- **AND THEN** the diagnostic directs the operator to the explicit `houmao-mgr project migrate` workflow

#### Scenario: Unsupported existing catalog fails with recreate guidance
- **WHEN** Houmao opens a project overlay whose existing catalog reports an unsupported schema version with no maintained migration
- **THEN** catalog initialization fails before mutating the catalog
- **AND THEN** the diagnostic directs the operator to restore, recreate, or reinitialize the project overlay

#### Scenario: Obsolete table shape is not repaired in place
- **WHEN** an existing project catalog reports the current schema version but still has an obsolete table constraint or removed column
- **THEN** Houmao treats the catalog as incompatible current-version state
- **AND THEN** Houmao fails explicitly instead of rebuilding catalog tables in place
