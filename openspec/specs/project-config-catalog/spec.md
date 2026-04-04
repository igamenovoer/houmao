# project-config-catalog Specification

## Purpose
TBD - created by archiving change refactor-config-storage-to-sqlite-catalog. Update Purpose after archive.
## Requirements
### Requirement: Project-local overlays persist canonical semantic configuration in a SQLite catalog

Project-local Houmao overlays SHALL store canonical semantic configuration in a SQLite catalog under the overlay root.

That catalog SHALL be the source of truth for project-local identities and relationships, including at minimum:

- specialists,
- roles,
- presets,
- setup profiles,
- skill packages,
- auth profiles,
- mailbox policies,
- references between those objects.

Project-local directory structure SHALL NOT remain the primary source of those semantic relationships once the catalog is present.

#### Scenario: Project-local specialist relationships are stored in the catalog
- **WHEN** an operator creates or updates a specialist in a project-local overlay
- **THEN** the project-local overlay persists the specialist's semantic identity and relationships in the SQLite catalog
- **AND THEN** the system does not need directory nesting alone to infer which role, preset, auth profile, or skill package that specialist uses

### Requirement: Project-local overlays keep large content payloads file-backed through managed content references

Project-local overlays SHALL keep large text blobs and tree-shaped payloads file-backed under managed overlay-owned content roots instead of requiring all content payloads to be stored inline in SQLite.

At minimum, this file-backed content contract SHALL cover:

- system prompt content,
- auth files,
- setup bundles,
- skill packages.

The SQLite catalog SHALL reference those file-backed payloads through explicit managed content references rather than by treating path nesting as the semantic graph.

#### Scenario: Prompt and auth payloads remain file-backed while relationships live in SQLite
- **WHEN** a project-local role uses one system prompt file and one auth profile uses one auth file
- **THEN** the project-local overlay keeps those payloads as managed files under overlay-owned content roots
- **AND THEN** the catalog stores the semantic references linking roles and auth profiles to those payload files

### Requirement: Project-local catalog surfaces stable advanced inspection semantics

The project-local catalog SHALL expose a stable advanced inspection surface suitable for SQL-based operator inspection.

At minimum, that surface SHALL provide:

- schema versioning,
- foreign-key-backed relationship integrity,
- stable read-oriented inspection tables or views for core project-local objects.

If advanced users manipulate project-local catalog state through SQL tools, the system SHALL define that surface intentionally rather than relying on undocumented path reconstruction behavior.

#### Scenario: Advanced operator inspects project-local semantic objects through SQL
- **WHEN** an advanced operator opens the project-local SQLite catalog with SQL tooling
- **THEN** they can inspect stable semantic objects such as specialists, roles, presets, and content references directly from the catalog
- **AND THEN** the inspection surface does not require reconstructing relationships from directory nesting under `.houmao/agents/`

### Requirement: Legacy project-local tree-backed overlays can be imported into the catalog

The system SHALL support one-way import of existing project-local overlays that currently encode semantic relationships through `.houmao/agents/` and `.houmao/easy/`.

That import SHALL:

- read legacy project-local specialist metadata and canonical tree content,
- create equivalent catalog-owned semantic objects and content references,
- establish the catalog as the authoritative project-local source of truth after successful import.

The system SHALL NOT require long-term dual-authoritative sync between the imported legacy tree and the new catalog.

#### Scenario: Existing project-local overlay is imported into the catalog
- **WHEN** an operator has an existing project-local overlay whose specialist, role, preset, auth, and skill relationships are stored through `.houmao/agents/` and `.houmao/easy/`
- **THEN** the system can import that overlay into the project-local SQLite catalog
- **AND THEN** the imported overlay resolves future project-local semantic relationships from the catalog rather than from the legacy tree as the source of truth

