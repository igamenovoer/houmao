## Purpose
Define how Houmao-owned system skills stay flat and tool-native across multiple logical workflow groups.
## Requirements
### Requirement: Houmao system skills keep flat visible projection across supported tools
The system SHALL support packaged Houmao-owned system skills from more than one logical workflow group without requiring visible family-specific projection paths.

Claude and Codex SHALL project installed Houmao-owned system skills into top-level Houmao-owned directories under `skills/`.

Gemini SHALL project installed Houmao-owned system skills into top-level Houmao-owned directories under `.gemini/skills/`.

#### Scenario: Codex installs mailbox and user-control skills into the same flat skill root
- **WHEN** Houmao installs one mailbox-oriented skill and one user-control skill into a Codex home
- **THEN** both skills project under top-level Houmao-owned skill directories in `skills/`
- **AND THEN** Codex does not require a visible family subdirectory for those installed skills

#### Scenario: Claude keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and user-control skills into a Claude home
- **THEN** both skills project into top-level Houmao-owned skill directories under `skills/`
- **AND THEN** Claude does not require a visible family subdirectory for those installed skills

#### Scenario: Gemini keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and user-control skills into a Gemini home
- **THEN** both skills project into top-level Houmao-owned skill directories under `.gemini/skills/`
- **AND THEN** Gemini does not require a visible family subdirectory for those installed skills

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

### Requirement: Houmao system skills keep flat visible projection when the touring skill group is installed
The system SHALL support the packaged `touring` logical skill group alongside the existing mailbox, advanced-usage, user-control, lifecycle, messaging, and gateway groups without changing the flat visible projection model.

Claude and Codex SHALL project installed `houmao-touring` into a top-level Houmao-owned directory under `skills/`.

Gemini SHALL project installed `houmao-touring` into a top-level Houmao-owned directory under `.gemini/skills/`.

#### Scenario: Codex installs touring with other skill groups into one flat root
- **WHEN** Houmao installs `houmao-touring` together with mailbox-oriented and user-control skills into a Codex home
- **THEN** all of those skills project under top-level Houmao-owned directories in `skills/`
- **AND THEN** Codex does not require a visible touring family subdirectory

#### Scenario: Gemini installs touring with other skill groups into one flat root
- **WHEN** Houmao installs `houmao-touring` together with other Houmao-owned system-skill groups into a Gemini home
- **THEN** all of those skills project under top-level Houmao-owned directories in `.gemini/skills/`
- **AND THEN** Gemini does not require a visible touring family subdirectory

### Requirement: Default Houmao-owned system-skill selection can include the touring logical group
The packaged current system-skill catalog SHALL support the touring logical group in the same default-selection model that already combines multiple logical groups.

Managed launch, managed join, and CLI-default installation SHALL preserve first-occurrence order when the touring set is selected together with the other named skill sets.

#### Scenario: CLI-default installation resolves touring with the other logical groups
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection includes the touring named set together with the existing default logical groups
- **AND THEN** each resolved skill still projects into the flat tool-native path appropriate for that tool

### Requirement: System-skill organization groups are separate from installable sets
Houmao documentation and catalog descriptions SHALL treat `automation`, `control`, `utils`, and `extensions` as conceptual organization groups when those labels are used.

The `automation`, `control`, and `utils` group labels SHALL NOT be treated as installable named sets unless they are explicitly declared under `[sets]` in the packaged catalog.

The `extensions` group SHALL be treated as an installable named set only because the packaged catalog explicitly declares `[sets.extensions]`.

The current installable named-set surface SHALL be `core`, `extensions`, and `all`.

#### Scenario: Operator sees organization groups and installable set names
- **WHEN** an operator reads system-skill documentation
- **THEN** skills may be grouped as automation, control, utils, and extensions for comprehension
- **AND THEN** install examples use `core`, `extensions`, `all`, or explicit skill names rather than undocumented organization labels

### Requirement: Utility logical group is included through all
The packaged current system-skill catalog SHALL include general utility skills in the `all` named set.

The utility logical group SHALL include `houmao-utils-workspace-mgr`.

The utility logical group SHALL NOT include `houmao-utils-llm-wiki`.

Utility skills that maintained core skills directly delegate to SHALL be included in the `core` named set.

#### Scenario: CLI default installation includes utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection expands `all`
- **AND THEN** the resolved selection includes `houmao-utils-workspace-mgr`
- **AND THEN** the resolved selection does not include `houmao-utils-llm-wiki`

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

### Requirement: System-skill families contain no Gemini provider guidance
Packaged current system-skill families SHALL NOT define Gemini-specific projection, credential, launch, or discovery behavior.

#### Scenario: Packaged skill audit excludes Gemini provider instructions
- **WHEN** maintainers scan current system-skill content and catalog metadata
- **THEN** no active provider route or example claims Gemini support
