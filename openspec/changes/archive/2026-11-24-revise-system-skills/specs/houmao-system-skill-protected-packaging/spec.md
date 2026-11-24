# System-Skill Protected Packaging Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Protected routines are composed only beneath executable entrypoints
**Reason**: The shared root is a static public sibling and owns the complete child inventory. Actor frames select eligible routes at invocation.

**Migration**: Use the sibling routing and static collection requirements for placement and eligibility.

### Requirement: Pack lifecycle operations are atomic and receipt-owned
**Reason**: The current lifecycle uses atomic, config-owned projection, and legacy receipts cannot establish ownership.

**Migration**: Use the system-skill installation requirements for ownership, rollback, and final-owner removal.

### Requirement: Copy and explicit symlink projection preserve complete composed trees
**Reason**: Static installation projects complete source roots without composed materializations.

**Migration**: Use the static collection requirements for byte-identical copy and explicit direct symlink projection.
