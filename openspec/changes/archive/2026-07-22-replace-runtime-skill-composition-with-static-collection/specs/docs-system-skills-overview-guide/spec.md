## ADDED Requirements

### Requirement: Overview guide explains the static six-skill collection
The getting-started system-skills overview SHALL list exactly the six standalone current system skills and SHALL distinguish them from the sixteen parent-scoped routines owned by `houmao-shared-routines`.

The guide SHALL explain that public means host-discoverable, while implicit invocation remains disabled for entrypoints, shared routines, and loops. It SHALL present admin welcome as the narrow first-user surface.

#### Scenario: Reader opens the current inventory section
- **WHEN** a reader opens the system-skills overview
- **THEN** the standalone inventory matches the six `public/*/SKILL.md` roots
- **AND THEN** shared children are presented as parent-scoped routes rather than independent install units

### Requirement: Overview guide explains sibling actor routing
The guide SHALL explain admin entrypoint, agent entrypoint, direct shared-routines, and direct loop posture. It SHALL show that actor entrypoints route ordinary work to the shared sibling and loop work to top-level loop siblings.

The guide SHALL NOT show shared routines nested beneath either entrypoint or describe a protected mount assembled at installation time.

#### Scenario: Reader follows an inspection example
- **WHEN** a reader wants human-operator inspection
- **THEN** the guide shows an admin-entrypoint route and explains its delegation to shared routines
- **AND THEN** it also identifies direct shared invocation as the advanced bypass

### Requirement: Overview guide documents both installation paths
The overview SHALL distinguish Houmao pack-aware installation from standard Skills CLI or copy-paste installation.

It SHALL provide complete admin and agent sibling lists for external installation, explain that Skills CLI does not resolve Houmao pack dependencies automatically, and show that exact discovery exposes six standalone roots.

#### Scenario: Reader chooses Skills CLI installation
- **WHEN** a reader follows the standard Agent Skills path
- **THEN** the guide provides an all-skills example and explicit actor-specific selections
- **AND THEN** it does not imply that selecting only an entrypoint installs its siblings

### Requirement: Overview guide preserves the guided-tour entry path
The overview SHALL present `$houmao-admin-welcome` as the state-aware, read-only first-user and reorientation route. It SHALL summarize the maintained guided paths and show executable handoff to the admin entrypoint.

#### Scenario: First-time reader wants orientation
- **WHEN** a reader does not yet know which operational route fits
- **THEN** the guide directs the reader to admin welcome
- **AND THEN** it does not replace the guided experience with the shared routine catalog
