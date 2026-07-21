## ADDED Requirements

### Requirement: System-skill manifest separates packs, public skills, and protected routines
Houmao SHALL package one schema-validated system-skill manifest that declares audience packs, public skills, protected mounts, and protected routine capabilities as distinct record types.

The manifest SHALL assign stable ids to packs and protected routines, stable public names to public skills, source paths contained under the packaged system-skill root, public roles, eligible audiences, route member names, dependencies, and default installation lanes.

Manifest loading SHALL validate the normalized payload against the packaged schema before resolving a pack or mutating a target home.

#### Scenario: Maintainer inspects the packaged manifest
- **WHEN** a maintainer loads the packaged system-skill manifest
- **THEN** the manifest identifies the `admin` and `agent` packs
- **AND THEN** it distinguishes public skill records from protected routine records
- **AND THEN** every source path resolves beneath the packaged system-skill root

#### Scenario: Invalid protected reference blocks installation
- **WHEN** a protected routine references an unknown pack, mount, audience, or dependency
- **THEN** manifest validation fails before pack composition begins
- **AND THEN** Houmao does not mutate the target home

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

### Requirement: Protected routines are composed only beneath executable entrypoints
Houmao SHALL compose the `houmao-shared-routines` protected mount beneath `houmao-admin-entrypoint` and `houmao-agent-entrypoint` using the audience route declared for the selected pack.

The composer SHALL include only protected routines eligible for that audience and their audience-valid dependency closure.

Houmao SHALL NOT project `houmao-shared-routines` or any protected routine as a top-level skill, and SHALL NOT mount protected content beneath `houmao-admin-welcome`.

#### Scenario: Admin pack receives an admin protected composition
- **WHEN** Houmao composes the admin pack
- **THEN** `houmao-admin-entrypoint/subskills/houmao-shared-routines` contains the admin route and admin-eligible routine closure
- **AND THEN** `houmao-admin-welcome` contains no protected mount
- **AND THEN** no protected routine is projected beside the two public skills

#### Scenario: Agent pack omits admin-only routines
- **WHEN** Houmao composes the agent pack
- **THEN** `houmao-agent-entrypoint/subskills/houmao-shared-routines` contains the agent route and agent-eligible routine closure
- **AND THEN** admin-only credential, project, agent-definition, and operator-messaging routines are absent from that composition

### Requirement: Pack validation is recursive and route-aware
Before committing a composed pack, Houmao SHALL recursively validate each public `SKILL.md`, every included protected `SKILL.md`, required frontmatter, route-name uniqueness, declared commands, direct-subskill route summaries, actor-guard markers, source containment, and dependency closure.

Validation SHALL reject a protected directory represented as a subskill when it lacks its own `SKILL.md`, and SHALL reject a procedure page represented as a subskill when it owns no independent skill package.

#### Scenario: Nested protected skill fails recursive validation
- **WHEN** a staged protected subskill lacks required metadata, its `SKILL.md`, or its parent route summary
- **THEN** recursive validation fails before commit
- **AND THEN** none of the selected pack's public paths are replaced

#### Scenario: Audience route omits a dependency
- **WHEN** an audience-eligible routine depends on another routine that is not eligible or included for that audience
- **THEN** validation reports the broken dependency closure
- **AND THEN** pack composition does not proceed

### Requirement: Pack lifecycle operations are atomic and receipt-owned
Install, upgrade, and uninstall SHALL treat every selected pack as a transaction and SHALL treat the two admin public skills as indivisible members of one pack.

The installer SHALL stage and validate all selected public trees, preflight every destination, back up receipt-owned destinations, commit all selected public paths, and write one versioned receipt containing pack ids, public paths, protected logical ids, projection mode, content digests, and materialization paths.

If commit or receipt persistence fails, Houmao SHALL restore the prior public paths and receipt. Uninstall SHALL remove only paths and materializations owned by the receipt.

#### Scenario: Admin entrypoint commit fails after welcome staging
- **WHEN** an admin-pack transaction cannot commit the entrypoint after staging both public siblings
- **THEN** the transaction restores the previous welcome and entrypoint state
- **AND THEN** it does not leave a newly installed welcome without its matching entrypoint

#### Scenario: Status detects a partial pack
- **WHEN** a receipt declares the admin pack but one public sibling or protected mount is missing
- **THEN** status classifies the pack as incomplete or drifted
- **AND THEN** it does not report the admin pack as healthy

### Requirement: Copy and explicit symlink projection preserve complete composed trees
Copy projection SHALL copy each staged composed public tree into its tool-native public path and SHALL remain the default for external and managed homes.

Explicit symlink projection SHALL create a receipt-owned composed materialization beneath the target tool home and SHALL link each public tool-native path to the complete corresponding materialized tree.

The installer SHALL NOT link a public entrypoint directly to an uncomposed source directory that lacks its protected mount.

#### Scenario: Explicit symlink install links complete admin siblings
- **WHEN** an operator explicitly installs the admin pack in symlink mode
- **THEN** both public paths link to receipt-owned composed materializations
- **AND THEN** the entrypoint materialization includes its protected admin routine mount
- **AND THEN** the welcome materialization remains self-contained

### Requirement: Legacy flat projections are migrated conservatively
Upgrade SHALL recognize the previous catalog's reserved flat `houmao-*` paths but SHALL remove one automatically only when it is linked to the packaged source or matches a known packaged content digest.

Unknown, modified, or untracked legacy paths SHALL be preserved and reported as conflicts. Fresh installation SHALL NOT silently delete a legacy path merely because its name is reserved.

#### Scenario: Known unmodified flat installation upgrades safely
- **WHEN** upgrade finds old flat paths whose content matches known packaged assets
- **THEN** it may remove those paths after the replacement pack is staged and validated
- **AND THEN** it records the removed paths in the new receipt

#### Scenario: Modified legacy skill is preserved
- **WHEN** upgrade finds a known old flat skill name whose content does not match a known packaged digest
- **THEN** upgrade reports the exact conflicting path
- **AND THEN** it preserves the path and does not guess that Houmao still owns it

