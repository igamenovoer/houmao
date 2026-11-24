# houmao-system-skill-protected-packaging Specification

## Purpose
Define how audience-specific system-skill packs declare and compose public entrypoints with protected routines. Recursive validation and receipt-owned transactions govern pack installation, upgrade, and removal.
## Requirements
### Requirement: System-skill manifest separates packs, public skills, and protected routines
The schema-validated system-skill manifest SHALL declare actor packs, standalone public skills, and shared child routines as distinct records. It SHALL declare stable IDs, contained paths, roles, audiences, route names, dependencies, and default lanes as applicable.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Manifest loading SHALL validate the normalized payload before resolving a pack or mutating a target home.

#### Scenario: Maintainer inspects the packaged manifest
- **WHEN** a maintainer loads the packaged manifest
- **THEN** it identifies the admin and agent packs and distinguishes standalone sources from shared child sources
- **AND THEN** every source path resolves beneath the packaged system-skill root

#### Scenario: Invalid protected reference blocks installation
- **WHEN** a routine references an unknown pack, audience, or dependency
- **THEN** manifest validation fails before the target home is mutated

### Requirement: Pack role cardinality is audience-specific
The `admin` pack SHALL contain exactly one public `welcome` role named `houmao-admin-welcome` and exactly one public `entrypoint` role named `houmao-admin-entrypoint`.

The `agent` pack SHALL contain exactly one public `entrypoint` role named `houmao-agent-entrypoint` and SHALL NOT require or declare a public welcome role.

The manifest validator SHALL apply role cardinality by pack kind rather than assuming that every pack has the same public-role shape.

#### Scenario: Valid admin and agent packs use different role shapes
- **WHEN** the packaged manifest is validated
- **THEN** the admin pack is valid only when both public siblings are present
- **AND THEN** the agent pack is valid with its entrypoint and no welcome sibling

#### Scenario: Partial admin pack is rejected
- **WHEN** the admin pack omits either `houmao-admin-welcome` or `houmao-admin-entrypoint`
- **THEN** manifest validation fails
- **AND THEN** Houmao does not expose the remaining public skill as an independently installable admin pack

### Requirement: Pack validation is recursive and route-aware
Before committing a static pack, Houmao SHALL validate public `SKILL.md` roots and shared `SKILL-MAIN.md` children. Validation SHALL check required metadata, owned entrypoint and resource paths, unique declared route names, commands, direct-child route declarations, and audience-valid dependency closure.

#### Scenario: Nested protected skill fails recursive validation
- **WHEN** a declared shared child lacks its role-canonical entrypoint, required metadata, or parent route declaration
- **THEN** source validation fails before commit
- **AND THEN** the installer preserves the existing selected pack paths

#### Scenario: Audience route omits a dependency
- **WHEN** an audience-eligible routine depends on a child that is ineligible for that audience
- **THEN** validation reports the broken dependency closure
- **AND THEN** pack installation does not proceed

### Requirement: Legacy flat projections are migrated conservatively
Upgrade SHALL remove a recognized legacy flat projection only when it links to the packaged source or matches a known packaged digest. Modified, unknown, and untracked paths SHALL be preserved and reported as conflicts. Fresh installation SHALL preserve paths reserved only by a previous catalog.

#### Scenario: Known unmodified flat installation upgrades safely
- **WHEN** upgrade finds a legacy flat skill path matching a packaged asset
- **THEN** it may remove the individually recognized path after the replacement pack is staged and validated
- **AND THEN** it reports the removed path in the upgrade result

#### Scenario: Modified legacy skill is preserved
- **WHEN** upgrade finds an old flat skill path without matching package-link or digest evidence
- **THEN** it reports and preserves the exact conflicting path

