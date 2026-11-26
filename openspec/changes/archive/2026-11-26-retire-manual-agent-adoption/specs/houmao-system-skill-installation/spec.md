# Spec Delta

## MODIFIED Requirements

### Requirement: Shared installer supports the universal Agent Skills projection target
The shared system-skill installer SHALL support `universal` as an explicit installation target for Houmao-owned system skills.

For the `universal` target, the visible projected paths SHALL use the cross-client Agent Skills root:

- Universal: `skills/<houmao-skill>/` under the resolved universal home root, which defaults to `~/.agents` for the operator CLI.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The shared installer SHALL apply the same current-skill selection, retired-skill cleanup, status discovery, uninstall, copied projection, and symlink projection behavior to the `universal` target that it applies to existing `skills/`-root targets.

The `universal` target SHALL NOT imply a runtime tool adapter, credential home, launch backend, or managed-agent provider.

Houmao-managed launch flows SHALL continue installing managed system skills into the selected runtime tool home and SHALL NOT silently duplicate those skills into the `universal` target.

#### Scenario: Explicit universal copy installation projects selected skills under skills root
- **WHEN** Houmao installs selected current system skills for target `universal` into resolved home `/home/alice/.agents` without symlink projection
- **THEN** each selected skill is copied under `/home/alice/.agents/skills/<houmao-skill>/`
- **AND THEN** the result reports projected relative directories under `skills/`

#### Scenario: Explicit universal symlink installation uses existing projection mode
- **WHEN** Houmao installs one selected current system skill for target `universal` with symlink projection
- **THEN** the projected path is `skills/<houmao-skill>/`
- **AND THEN** that path is a directory symlink to the packaged skill asset root

#### Scenario: Universal uninstall removes only universal projections
- **WHEN** Houmao uninstalls system skills for target `universal` with resolved home `/home/alice/.agents`
- **THEN** it removes current and retired Houmao-owned projections under `/home/alice/.agents/skills/`
- **AND THEN** it does not remove projections from `.codex/skills/`, `.kimi-code/skills/`, `.gemini/skills/`, `.github/skills/`, or `.claude/skills/`

#### Scenario: Managed runtime install does not write universal target
- **WHEN** Houmao builds a managed runtime home for one concrete agent tool
- **THEN** managed system skills are installed into that runtime tool home's native projection root
- **AND THEN** Houmao does not also install those skills into `~/.agents/skills`

### Requirement: Lifecycle operations do not enforce skill release metadata
System-skill install, sync, upgrade, status, uninstall, managed launch, rebuild, relaunch, prompt generation, and skill invocation SHALL NOT require or compare installed `houmao_version` values.

Copy projection SHALL preserve the checked-in frontmatter bytes. Symlink projection SHALL expose the checked-in source unchanged. The manifest, skill config, content digest, ownership, policy, and transaction rules SHALL remain authoritative for lifecycle operations.

#### Scenario: Existing installation has no version field
- **WHEN** a lifecycle operation encounters an installed root without `houmao_version`
- **THEN** it applies the current config, content, ownership, and conflict rules
- **AND THEN** it does not fail solely because version metadata is missing

#### Scenario: Installed version differs from running Houmao
- **WHEN** managed launch or synchronization encounters a version mismatch
- **THEN** version equality does not become a lifecycle precondition
- **AND THEN** only an explicit doctor invocation reports the mismatch as version evidence

### Requirement: Shared installer resolves audience packs rather than peer skill sets
The shared system-skill installer SHALL accept one or more pack ids and SHALL resolve each id to its complete static standalone membership.

CLI-default external-home installation SHALL resolve the five-member `admin` pack. Managed launch, rebuild, and relaunch SHALL resolve the four-member `agent` pack. Explicit repeated selection MAY resolve both packs, but SHALL NOT merge their actor identities or create duplicate shared destinations.

#### Scenario: External install omits selectors
- **WHEN** an operator installs Houmao system skills into an external supported tool home without a pack selector
- **THEN** the installer resolves the complete admin pack
- **AND THEN** it installs welcome, admin entrypoint, shared routines, pro loop, and lite loop

#### Scenario: Managed launch uses agent default
- **WHEN** managed launch resolves default Houmao system-skill installation
- **THEN** it resolves only the agent pack
- **AND THEN** it installs agent entrypoint, shared routines, pro loop, and lite loop without either admin root

### Requirement: Managed defaults install the complete static agent pack
Managed launch, rebuild, and relaunch SHALL install or synchronize the complete static agent pack in copy mode unless valid policy disables or replaces that selection.

The managed home SHALL contain the agent entrypoint, shared routines, pro loop, and lite loop as top-level siblings. Admin welcome and admin entrypoint SHALL remain absent by default.

#### Scenario: Managed launch uses omitted system-skill policy
- **WHEN** a new managed home is built with the default selection
- **THEN** all four static agent-pack members are copied into the tool-native root
- **AND THEN** no runtime composition directory or admin public skill is created
