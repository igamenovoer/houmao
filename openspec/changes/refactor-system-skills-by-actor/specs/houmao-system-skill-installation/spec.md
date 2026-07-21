## ADDED Requirements

### Requirement: Shared installer resolves audience packs rather than peer skill sets
The shared system-skill installer SHALL accept one or more pack ids and SHALL resolve each id to its complete public-role and protected-mount composition.

CLI-default external-home installation SHALL resolve the `admin` pack. Managed launch, rebuild, relaunch, and join SHALL resolve the `agent` pack. Explicit repeated selection MAY resolve both packs, but SHALL NOT merge their actor identities or partial members.

#### Scenario: External install omits selectors
- **WHEN** an operator installs Houmao system skills into an external supported tool home without a pack selector
- **THEN** the installer resolves the complete admin pack
- **AND THEN** it installs both admin public siblings

#### Scenario: Managed launch uses agent default
- **WHEN** managed launch resolves default Houmao system-skill installation
- **THEN** it resolves only the agent pack
- **AND THEN** it does not install either admin public skill by default

### Requirement: Shared installer projects complete public skills into supported tool homes
The shared installer SHALL project only public skills at the established tool-native top-level skill root for Claude, Codex, Copilot, Kimi, and the universal Agent Skills target.

Protected routine trees SHALL be nested inside executable entrypoint projections. Copy SHALL remain the default mode, managed homes SHALL use copy, and explicit symlink mode SHALL link complete receipt-owned composed public trees.

#### Scenario: Codex admin pack uses public top-level paths
- **WHEN** the admin pack is installed into a Codex home
- **THEN** `skills/houmao-admin-welcome/` and `skills/houmao-admin-entrypoint/` are the top-level Houmao projections
- **AND THEN** protected routines appear only beneath the entrypoint

#### Scenario: Kimi managed home receives agent entrypoint
- **WHEN** Houmao installs the managed default into a Kimi Code CLI home
- **THEN** the Kimi skill root receives top-level `houmao-agent-entrypoint`
- **AND THEN** its protected routines are nested beneath that entrypoint

### Requirement: Managed system-skill policy selects packs
Stored source and launch-profile system-skill policy SHALL retain the supported policy modes `default`, `inherit`, `extend`, `replace`, and `none` where each lane permits them, but SHALL store and resolve `packs` rather than `sets` and `skills`.

The policy resolver SHALL reject unknown pack ids, invalid mode and selector combinations, and any attempt to select a protected logical id as an install unit. System-skill policy SHALL continue to exclude managed auto skills.

#### Scenario: Profile extends source policy with admin pack
- **WHEN** a valid profile policy extends a source selection with the admin pack
- **THEN** the resolver returns complete, deduplicated pack ids in first-occurrence order
- **AND THEN** protected members are derived from the manifest rather than persisted as selectors

#### Scenario: Policy selects a protected logical id
- **WHEN** stored policy names `houmao-agent-inspect` as if it were an installable pack
- **THEN** policy validation fails
- **AND THEN** managed home construction does not begin

### Requirement: Install and removal use pack ownership receipts
Install, sync, status, upgrade, and uninstall SHALL use the versioned pack receipt as the authoritative ownership record after a successful pack transaction.

Sync SHALL replace the exact receipt-owned pack selection while preserving unrelated user-authored skills. Uninstall SHALL remove only selected receipt-owned packs and SHALL report absent, incomplete, drifted, and conflicting pack state explicitly.

#### Scenario: Managed home changes from both packs to agent only
- **WHEN** sync resolves the agent pack and the receipt currently owns both packs
- **THEN** sync removes the receipt-owned admin public siblings as one pack
- **AND THEN** it preserves the agent pack and unrelated user-authored skills

#### Scenario: Untracked public-name collision blocks install
- **WHEN** a target public path exists but is not owned by the receipt
- **THEN** installation fails with the exact conflicting path
- **AND THEN** it does not overwrite the untracked directory

## REMOVED Requirements

### Requirement: Current Houmao-owned system skills are packaged as maintained runtime assets
**Reason**: The flat per-skill catalog contract is replaced by the pack, public-skill, protected-mount, and protected-routine manifest.
**Migration**: Use the manifest and audience-pack records defined by `houmao-system-skill-protected-packaging`.

### Requirement: Packaged catalog uses the renamed AG-UI interop skill
**Reason**: Individual low-level routines are no longer independent catalog install units.
**Migration**: Route the protected `houmao-interop-ag-ui` logical routine through an eligible public entrypoint.

### Requirement: Shared installer projects selected current Houmao-owned skills into target tool homes
**Reason**: The installer now projects complete public pack members and nests protected routines.
**Migration**: Select an audience pack and use its public entrypoint path.

### Requirement: Shared installer supports named set selection and explicit current-skill selection
**Reason**: Named sets and explicit protected-skill selection are removed.
**Migration**: Use repeatable audience pack selection.

### Requirement: Packaged system-skill catalog includes the advanced-usage skill and default set selection
**Reason**: The advanced-usage routine is protected and its eligibility comes from the audience matrix.
**Migration**: Invoke it through an eligible public entrypoint.

### Requirement: Packaged system-skill catalog includes `houmao-touring` and a dedicated touring set
**Reason**: `houmao-touring` and the touring set are retired.
**Migration**: Install the admin pack and use `houmao-admin-welcome`.

### Requirement: Packaged system-skill catalog includes `houmao-agent-inspect` and a dedicated inspect set
**Reason**: Inspect is a protected shared routine rather than an independently selected set.
**Migration**: Use the `agent-inspect` route through an eligible entrypoint.

### Requirement: Packaged system-skill catalog includes all pairwise variants in the current install sets
**Reason**: Retired pairwise variants do not belong to the new pack manifest.
**Migration**: Use the maintained protected pro or lite loop route.

### Requirement: Packaged system-skill catalog replaces relay loop planner with generic loop planner
**Reason**: Historical loop-name replacement no longer defines current pack selection.
**Migration**: Use protected `houmao-agent-loop-pro` or `houmao-agent-loop-lite` through an eligible entrypoint.

### Requirement: Packaged system-skill catalog includes managed-memory guidance
**Reason**: Memory guidance is selected as a protected audience routine, not a peer catalog entry.
**Migration**: Use the protected memory route through an eligible entrypoint.

### Requirement: Shared installer overwrites selected current skill projections without install state
**Reason**: Stateless overwrite cannot manage multi-public packs safely.
**Migration**: Use staged pack transactions and versioned ownership receipts.

### Requirement: Shared system-skill removal removes all current catalog-known projections
**Reason**: Name-based global removal risks deleting untracked or modified content.
**Migration**: Uninstall receipt-owned packs; use explicit legacy conflict resolution for untracked paths.

### Requirement: Installable system-skill sets are closed over internal skill routing
**Reason**: Installable sets are removed.
**Migration**: Validate protected dependency closure per audience pack.

### Requirement: Packaged workspace utility skill is available through core and all
**Reason**: `core` and `all` no longer exist.
**Migration**: Use the shared workspace route through either eligible entrypoint.

### Requirement: Packaged catalog marks unified agent definition as canonical
**Reason**: Canonical ownership now belongs to a protected logical routine rather than a flat catalog annotation.
**Migration**: Route specialist, profile, recipe, and launch-dossier work to protected `houmao-agent-definition` through the admin entrypoint.

### Requirement: Packaged catalog exposes pro as the only current loop skill
**Reason**: Current loop selection is expressed by protected routine eligibility and includes maintained pro and lite routes.
**Migration**: Use the entrypoint-qualified pro or lite route.

### Requirement: Shared installer cleans known retired loop skill projections
**Reason**: Unconditional name-based cleanup is replaced by conservative legacy classification.
**Migration**: Run pack upgrade and resolve any drifted legacy paths it reports.

### Requirement: Shared removal includes known retired loop projections
**Reason**: Receipt-owned uninstall cannot claim untracked legacy paths automatically.
**Migration**: Use explicit legacy cleanup after status or upgrade classifies the old paths.

### Requirement: Retired loop skill sources are preserved only as source legacy references
**Reason**: The new protected bundle does not carry old public wrapper sources.
**Migration**: Keep historical behavior in OpenSpec and version control rather than current packaged assets.

### Requirement: Packaged catalog exposes pro and lite as current loop skills
**Reason**: Pro and lite remain maintained behaviors but are not independent catalog entries.
**Migration**: Route both protected routines through an eligible public entrypoint.

### Requirement: Shared installer projects the lite skill as a normal current system skill
**Reason**: Lite is no longer a top-level projected skill.
**Migration**: Use the entrypoint-qualified protected lite route.

### Requirement: Managed launch system-skill installation accepts resolved source policy
**Reason**: The old resolved policy payload contains set and skill selectors.
**Migration**: Persist and resolve pack ids with the retained policy modes.

### Requirement: Packaged catalog includes the operator messaging skill in default control sets
**Reason**: Control sets are removed and operator messaging is admin-only protected content.
**Migration**: Use the operator-messaging route through `houmao-admin-entrypoint`.

