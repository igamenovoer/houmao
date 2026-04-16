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
The packaged current system-skill catalog SHALL support named sets and default auto-install selections that include skills from more than one logical workflow group.

Managed launch, managed join, and CLI-default installation SHALL preserve first-occurrence order across those selected sets while projecting each selected skill into its flat tool-native visible path.

#### Scenario: CLI default installation resolves mailbox and user-control sets together
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection includes both the mailbox default set and the user-control set
- **AND THEN** each installed skill projects into the visible path appropriate for its family

#### Scenario: Install state records flat projected paths
- **WHEN** Houmao installs mailbox-oriented and user-control skills into the same supported tool home
- **THEN** the recorded Houmao-owned install state includes the flat projected relative directories for those skills
- **AND THEN** later reinstall or collision checks use those exact flat owned paths

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

### Requirement: Utility logical group is represented by an explicit named set
The packaged current system-skill catalog SHALL represent general utility skills through a `utils` named set.

The `utils` set SHALL include `houmao-utils-llm-wiki`.

The `utils` set SHALL be explicit-only and SHALL NOT be part of managed launch, managed join, or CLI-default installation selections.

#### Scenario: Operator lists logical skill groups
- **WHEN** an operator lists the packaged Houmao-owned system skills and named sets
- **THEN** the named sets include `utils`
- **AND THEN** `utils` contains `houmao-utils-llm-wiki`
- **AND THEN** the default-selection metadata does not include `utils`

#### Scenario: Explicit default installation omits utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection does not include `houmao-utils-llm-wiki`
