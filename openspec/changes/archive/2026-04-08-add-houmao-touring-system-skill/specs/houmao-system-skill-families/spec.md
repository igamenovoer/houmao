## ADDED Requirements

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
