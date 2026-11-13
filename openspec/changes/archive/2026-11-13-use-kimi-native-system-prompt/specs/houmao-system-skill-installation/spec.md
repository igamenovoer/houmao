## MODIFIED Requirements

### Requirement: Version metadata remains diagnostic in lifecycle configuration
The v5 system-skill manifest SHALL remain the static collection authority. It SHALL contain no managed auto-skill ownership field. `houmao-skill-config.v1` SHALL record one collection-level `houmao_version` and complete-tree digests without duplicating a required per-skill release field.

Doctor SHALL read each installed root's frontmatter directly and SHALL NOT migrate or rewrite the skill config while diagnosing versions.

#### Scenario: Current pack is installed with release metadata
- **WHEN** install projects a versioned standalone root
- **THEN** its complete-tree digest naturally covers the frontmatter bytes
- **AND THEN** the config records the installing Houmao release separately from per-root frontmatter

#### Scenario: Doctor reads a current config
- **WHEN** doctor examines a lifecycle-managed home
- **THEN** it leaves the config bytes unchanged
- **AND THEN** it reads observed skill versions from installed `SKILL.md` files

### Requirement: Managed system-skill policy selects packs
Stored source and launch-profile system-skill policy SHALL retain the supported policy modes `default`, `inherit`, `extend`, `replace`, and `none` where each lane permits them, but SHALL store and resolve `packs` rather than `sets` and `skills`.

The policy resolver SHALL reject unknown pack ids, invalid mode and selector combinations, and any attempt to select a protected logical id as an install unit. System-skill policy SHALL govern only catalog-backed system-skill packs; provider-native role-prompt files are brain construction outputs rather than skill install units.

#### Scenario: Profile extends source policy with admin pack
- **WHEN** a valid profile policy extends a source selection with the admin pack
- **THEN** the resolver returns complete, deduplicated pack ids in first-occurrence order
- **AND THEN** protected members are derived from the manifest rather than persisted as selectors

#### Scenario: Policy selects a protected logical id
- **WHEN** stored policy names `houmao-agent-inspect` as if it were an installable pack
- **THEN** policy validation fails
- **AND THEN** managed home construction does not begin

#### Scenario: Native role prompt is not a system-skill selector
- **WHEN** a managed Kimi brain resolves a native `SYSTEM.md` role prompt
- **THEN** the system-skill policy contains no selector or ownership record for that file
- **AND THEN** system-skill lifecycle commands do not install or remove the native role prompt

### Requirement: Shared installer resolves packs to static standalone members
The shared system-skill installer SHALL resolve the `admin` and `agent` pack ids to deduplicated standalone skill records from the v5 manifest.

The admin pack SHALL resolve to `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`. The agent pack SHALL resolve to `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.

#### Scenario: Both packs are selected
- **WHEN** an operator explicitly selects both admin and agent packs
- **THEN** the installer resolves six unique standalone skills
- **AND THEN** shared routines and both loop skills occur once in first-occurrence order

## REMOVED Requirements

### Requirement: System-skill policy does not control managed auto skills
**Reason**: The managed auto-skill projection lane has been deleted; native provider prompt files remain outside system-skill packs by construction.

**Migration**: Remove auto-skill policy assumptions and use native provider prompt provenance for role-delivery diagnostics.
