## MODIFIED Requirements

### Requirement: Project-local overlays persist canonical semantic configuration in a SQLite catalog
Project-local Houmao overlays SHALL store canonical semantic configuration in a SQLite catalog under the overlay root.

That catalog SHALL be the source of truth for project-local identities and relationships, including at minimum:

- specialists,
- launch templates,
- roles,
- recipes projected under `.houmao/agents/presets/`,
- setup profiles,
- skill packages,
- auth profiles,
- mailbox policies,
- references between those objects.

Project-local directory structure SHALL NOT remain the primary source of those semantic relationships once the catalog is present.

#### Scenario: Project-local launch-template relationships are stored in the catalog
- **WHEN** an operator creates or updates a launch template in a project-local overlay
- **THEN** the project-local overlay persists that template's semantic identity and source relationships in the SQLite catalog
- **AND THEN** the system does not need directory nesting alone to infer which specialist or recipe the template uses

### Requirement: Project-local overlays keep large content payloads file-backed through managed content references
Project-local overlays SHALL keep large text blobs and tree-shaped payloads file-backed under managed overlay-owned content roots instead of requiring all content payloads to be stored inline in SQLite.

At minimum, this file-backed content contract SHALL cover:

- system prompt content,
- launch-template prompt overlay content,
- auth files,
- setup bundles,
- skill packages.

The SQLite catalog SHALL reference those file-backed payloads through explicit managed content references rather than by treating path nesting as the semantic graph.

#### Scenario: Launch-template prompt overlay remains file-backed while relationships live in SQLite
- **WHEN** one launch template stores prompt overlay text for template `alice`
- **THEN** the project-local overlay keeps that prompt-overlay payload as managed file-backed content under the overlay-owned content roots
- **AND THEN** the catalog stores the semantic references linking launch template `alice` to that prompt-overlay payload
