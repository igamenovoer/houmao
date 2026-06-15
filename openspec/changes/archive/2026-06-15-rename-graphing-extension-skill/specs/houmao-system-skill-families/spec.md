## MODIFIED Requirements

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
The packaged current system-skill catalog SHALL support default auto-install selections that include skills from more than one logical workflow group while exposing only the current installable named sets.

The current installable named sets SHALL be `core`, `extensions`, and `all`.

Managed launch, managed join, and CLI-default installation SHALL preserve first-occurrence order across the selected set contents while projecting each selected skill into its flat tool-native visible path.

Managed launch and managed join defaults SHALL resolve the `core` set followed by the `extensions` set.

CLI-default installation SHALL resolve the `all` set.

#### Scenario: CLI default installation resolves the all set
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection expands the `all` set
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Managed default installation resolves core and extensions
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the resolved selection expands `core` and `extensions` in that order
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Install state records flat projected paths
- **WHEN** Houmao installs system skills from multiple logical workflow groups into the same supported tool home
- **THEN** the recorded or discovered Houmao-owned install surface uses the flat projected relative directories for those skills
- **AND THEN** later reinstall, status, or collision checks use those exact flat owned paths

### Requirement: System-skill organization groups are separate from installable sets
Houmao documentation and catalog descriptions SHALL treat `automation`, `control`, `utils`, and `extensions` as conceptual organization groups when those labels are used.

The `automation`, `control`, and `utils` group labels SHALL NOT be treated as installable named sets unless they are explicitly declared under `[sets]` in the packaged catalog.

The `extensions` group SHALL be treated as an installable named set only because the packaged catalog explicitly declares `[sets.extensions]`.

The current installable named-set surface SHALL be `core`, `extensions`, and `all`.

#### Scenario: Operator sees organization groups and installable set names
- **WHEN** an operator reads system-skill documentation
- **THEN** skills may be grouped as automation, control, utils, and extensions for comprehension
- **AND THEN** install examples use `core`, `extensions`, `all`, or explicit skill names rather than undocumented organization labels

## ADDED Requirements

### Requirement: Extension skills are default-installed without becoming core dependencies
The packaged current system-skill catalog SHALL include extension skills in the `extensions` named set.

The `core` named set SHALL remain the non-extension baseline and SHALL NOT include `houmao-ext-graphing`.

The `all` named set SHALL include extension skills.

Managed launch and managed join defaults SHALL include extension skills by resolving the `extensions` named set after `core`.

Non-extension packaged system skills SHALL NOT require, delegate to, or route ordinary task handling through extension skills.

#### Scenario: Managed default installation includes extensions after core
- **WHEN** Houmao installs system skills for managed launch or join
- **THEN** the resolved selection includes current `core` skills
- **AND THEN** the resolved selection includes current `extensions` skills after the first occurrence of each selected core skill

#### Scenario: Explicit core install omits graphing extension
- **WHEN** an operator explicitly installs `--skill-set core`
- **THEN** the resolved selection does not include `houmao-ext-graphing`
- **AND THEN** the operator can install the graphing extension through `--skill-set extensions`, `--skill-set all`, or `--skill houmao-ext-graphing`

#### Scenario: Non-extension skills do not route to graphing extension
- **WHEN** an agent reads a packaged non-extension system skill
- **THEN** the skill does not present `houmao-ext-graphing` as a required related skill, delegated workflow, or routing target
- **AND THEN** users can ignore extension skills without breaking non-extension skill guidance
