## ADDED Requirements

### Requirement: Houmao system skills keep flat visible projection across supported tools
The system SHALL support packaged Houmao-owned system skills from more than one logical workflow group without requiring visible family-specific projection paths.

Claude and Codex SHALL project installed Houmao-owned system skills into top-level Houmao-owned directories under `skills/`.

Gemini SHALL project installed Houmao-owned system skills into top-level Houmao-owned directories under `.agents/skills/`.

#### Scenario: Codex installs mailbox and project/easy skills into the same flat skill root
- **WHEN** Houmao installs one mailbox-oriented skill and one project/easy skill into a Codex home
- **THEN** both skills project under top-level Houmao-owned skill directories in `skills/`
- **AND THEN** Codex does not require a visible family subdirectory for those installed skills

#### Scenario: Claude keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and project/easy skills into a Claude home
- **THEN** both skills project into top-level Houmao-owned skill directories under `skills/`
- **AND THEN** Claude does not require a visible family subdirectory for those installed skills

#### Scenario: Gemini keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and project/easy skills into a Gemini home
- **THEN** both skills project into top-level Houmao-owned skill directories under `.agents/skills/`
- **AND THEN** Gemini does not require a visible family subdirectory for those installed skills

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
The packaged current system-skill catalog SHALL support named sets and default auto-install selections that include skills from more than one logical workflow group.

Managed launch, managed join, and CLI-default installation SHALL preserve first-occurrence order across those selected sets while projecting each selected skill into its flat tool-native visible path.

#### Scenario: CLI default installation resolves mailbox and project-easy sets together
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection includes both the mailbox default set and the project-easy authoring set
- **AND THEN** each installed skill projects into the visible path appropriate for its family

#### Scenario: Install state records flat projected paths
- **WHEN** Houmao installs mailbox-oriented and project/easy skills into the same supported tool home
- **THEN** the recorded Houmao-owned install state includes the flat projected relative directories for those skills
- **AND THEN** later reinstall or collision checks use those exact flat owned paths
