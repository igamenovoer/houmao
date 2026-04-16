# project-config-catalog Specification

## Purpose
TBD - created by archiving change refactor-config-storage-to-sqlite-catalog. Update Purpose after archive.
## Requirements
### Requirement: Project-local overlays persist canonical semantic configuration in a SQLite catalog

Project-local Houmao overlays SHALL store canonical semantic configuration in a SQLite catalog under the overlay root.

That catalog SHALL be the source of truth for project-local identities and relationships, including at minimum:

- specialists,
- launch profiles,
- roles,
- recipes projected under `.houmao/agents/presets/`,
- setup profiles,
- skill packages,
- auth profiles,
- mailbox policies,
- references between those objects,
- source-lane provenance that distinguishes specialist-backed easy profiles from recipe-backed explicit launch profiles.

Project-local directory structure SHALL NOT remain the primary source of those semantic relationships once the catalog is present.

#### Scenario: Project-local launch-profile relationships are stored in the catalog
- **WHEN** an operator creates or updates a launch profile in a project-local overlay
- **THEN** the project-local overlay persists that profile's semantic identity and source relationships in the SQLite catalog
- **AND THEN** the system does not need directory nesting alone to infer which specialist or recipe the profile uses

### Requirement: Project-local overlays keep large content payloads file-backed through managed content references

Project-local overlays SHALL keep large text blobs and tree-shaped payloads file-backed under managed overlay-owned content roots instead of requiring all content payloads to be stored inline in SQLite.

At minimum, this file-backed content contract SHALL cover:

- system prompt content,
- launch-profile prompt overlay content,
- auth files,
- setup bundles,
- skill packages.

The SQLite catalog SHALL reference those file-backed payloads through explicit managed content references rather than by treating path nesting as the semantic graph.

#### Scenario: Launch-profile prompt overlay remains file-backed while relationships live in SQLite
- **WHEN** one launch profile stores prompt overlay text for profile `alice`
- **THEN** the project-local overlay keeps that prompt-overlay payload as managed file-backed content under the overlay-owned content roots
- **AND THEN** the catalog stores the semantic references linking profile `alice` to that prompt-overlay payload

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

### Requirement: Project-local auth profiles use catalog-owned opaque storage identity
Project-local auth profiles SHALL be stored as catalog-owned semantic objects with distinct operator-facing display names and stable opaque storage identity.

At minimum, each persisted auth profile SHALL carry:

- the selected tool family,
- a mutable display name unique within that tool family,
- an immutable opaque bundle reference used for file-backed auth content storage and compatibility projection,
- a managed content reference for the auth payload.

Managed auth content SHALL be stored under bundle-reference-keyed managed content paths rather than display-name-keyed managed content paths.

Directory basenames under managed auth content or compatibility projection trees SHALL NOT be treated as the semantic identity of an auth profile.

#### Scenario: Newly created auth profile receives opaque storage identity
- **WHEN** an operator creates a new project-local Claude auth profile named `personal`
- **THEN** the catalog persists that auth profile with display name `personal`
- **AND THEN** the backing auth content is stored and later projected under an opaque bundle-reference path rather than a display-name-derived path

#### Scenario: Renaming auth profile does not change bundle-reference-backed content storage
- **WHEN** a project-local auth profile already exists with display name `work`
- **AND WHEN** that auth profile is renamed to `breakglass`
- **THEN** the catalog keeps the same opaque bundle reference and managed content reference for that auth profile
- **AND THEN** only the display-name metadata changes

### Requirement: Project-local auth relationships resolve through auth profile identity
Persisted project-local relationships that target auth profiles SHALL resolve through auth profile identity rather than storing auth display-name text as the relationship key.

At minimum, launch-profile auth overrides and specialist-owned auth selection SHALL resolve through the referenced auth profile instead of duplicating display-name identity as authoritative state.

User-facing inspection surfaces MAY render the current auth display name, but that rendered name SHALL be derived from the referenced auth profile rather than treated as the stored relationship key.

#### Scenario: Launch-profile auth relationship remains valid after auth rename
- **WHEN** an explicit launch profile references one existing Codex auth profile
- **AND WHEN** that auth profile is renamed from `work` to `breakglass`
- **THEN** the launch profile still resolves the same auth profile without requiring a launch-profile edit
- **AND THEN** later inspection renders the current display name `breakglass`

#### Scenario: Specialist inspection derives auth name from the referenced auth profile
- **WHEN** a persisted specialist references one existing auth profile
- **AND WHEN** that auth profile has display name `reviewer-creds`
- **THEN** specialist inspection renders `reviewer-creds` as the selected auth name
- **AND THEN** that rendered name comes from the referenced auth profile instead of a second authoritative stored name field

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

