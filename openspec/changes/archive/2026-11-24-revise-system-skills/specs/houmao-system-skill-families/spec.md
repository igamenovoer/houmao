# System-Skill Families Delta

## MODIFIED Requirements

### Requirement: Houmao system skills keep flat visible projection across supported tools
Each selected standalone system skill SHALL occupy one top-level directory under the tool-native skill root. The six public roots SHALL be siblings. All manifest-declared parent-scoped routines SHALL live under the shared root. Actor entrypoints SHALL contain no generated shared or loop root copies.

#### Scenario: Codex installs both actor packs into one flat skill root
- **WHEN** Houmao installs admin and agent packs into a Codex home
- **THEN** the Codex `skills/` directory contains exactly the six standalone Houmao roots
- **AND THEN** shared children remain nested only under `skills/houmao-shared-routines/subskills/`

#### Scenario: Claude installs the agent pack
- **WHEN** Houmao installs the agent pack into a Claude home
- **THEN** the four agent-pack members are top-level siblings under `skills/`
- **AND THEN** no visible workflow-family directory is required

#### Scenario: Codex installs mailbox and user-control skills into the same flat skill root
- **WHEN** an actor pack is installed into a Codex home
- **THEN** both kinds of routine live below the shared root under `skills/`

#### Scenario: Claude keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** an actor pack is installed into a Claude home
- **THEN** both kinds of routine live below the shared root under `skills/`

#### Scenario: Gemini keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** an operator requests projection into a Gemini skill home
- **THEN** Houmao rejects the unsupported tool target
