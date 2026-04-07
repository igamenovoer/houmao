## MODIFIED Requirements

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
