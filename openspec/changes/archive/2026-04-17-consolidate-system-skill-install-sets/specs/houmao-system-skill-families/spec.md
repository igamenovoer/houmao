## MODIFIED Requirements

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
The packaged current system-skill catalog SHALL support default auto-install selections that include skills from more than one logical workflow group while exposing only the current installable named sets.

The current installable named sets SHALL be `core` and `all`.

Managed launch, managed join, and CLI-default installation SHALL preserve first-occurrence order across the selected set contents while projecting each selected skill into its flat tool-native visible path.

#### Scenario: CLI default installation resolves the all set
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection expands the `all` set
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Managed default installation resolves the core set
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the resolved selection expands the `core` set
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Install state records flat projected paths
- **WHEN** Houmao installs system skills from multiple logical workflow groups into the same supported tool home
- **THEN** the recorded or discovered Houmao-owned install surface uses the flat projected relative directories for those skills
- **AND THEN** later reinstall, status, or collision checks use those exact flat owned paths

## ADDED Requirements

### Requirement: System-skill organization groups are separate from installable sets
Houmao documentation and catalog descriptions SHALL treat `automation`, `control`, and `utils` as conceptual organization groups when those labels are used.

Those group labels SHALL NOT be treated as installable named sets unless they are explicitly declared under `[sets]` in the packaged catalog.

The current installable named-set surface SHALL remain `core` and `all`.

#### Scenario: Operator sees organization groups without extra installable set names
- **WHEN** an operator reads system-skill documentation
- **THEN** skills may be grouped as automation, control, and utils for comprehension
- **AND THEN** install examples use `core`, `all`, or explicit skill names rather than `automation`, `control`, or `utils`

### Requirement: Utility logical group is included through all
The packaged current system-skill catalog SHALL include general utility skills in the `all` named set.

The utility logical group SHALL include `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`.

The utility logical group SHALL NOT be installed by managed launch or managed join defaults unless a future change adds utility skills to `core`.

#### Scenario: CLI default installation includes utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection expands `all`
- **AND THEN** the resolved selection includes `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

#### Scenario: Managed default installation omits utility group
- **WHEN** Houmao installs system skills for managed launch or join
- **THEN** the resolved selection expands `core`
- **AND THEN** the resolved selection omits the utility logical group

## REMOVED Requirements

### Requirement: Utility logical group is represented by an explicit named set
**Reason**: The former explicit-only `utils` named set has been replaced by documentation-level utility grouping plus the installable `all` set.

**Migration**: Use `--skill-set all` to install all utility skills, or use explicit `--skill` values for a narrower utility install.

#### Scenario: Utility skills no longer require the utils set
- **WHEN** an operator wants the packaged utility skills
- **THEN** the supported named-set selection is `all`
- **AND THEN** `utils` is not required or documented as a current set name
