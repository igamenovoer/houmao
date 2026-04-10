## ADDED Requirements

### Requirement: Project-local auth profiles can be renamed without changing stable identity
The system SHALL allow an existing project-local auth profile to change its operator-facing display name without changing the underlying auth profile identity, opaque bundle reference, or referenced auth content.

Rename SHALL mutate only the display-name metadata for the selected tool family.

Rename SHALL preserve all existing downstream relationships that already reference that auth profile.

#### Scenario: Rename preserves the underlying auth profile identity
- **WHEN** a Codex auth profile exists with display name `work`
- **AND WHEN** an operator renames that auth profile to `breakglass`
- **THEN** the auth profile continues to reference the same auth content payload
- **AND THEN** the auth profile keeps the same stable internal identity and opaque bundle reference

#### Scenario: Rename updates the operator-facing name used by later commands
- **WHEN** a Claude auth profile exists with display name `personal`
- **AND WHEN** an operator renames it to `logged-in`
- **THEN** later supported auth-management commands resolve that auth profile by `logged-in`
- **AND THEN** those commands no longer require the old display name `personal`

#### Scenario: Rename rejects duplicate display names within one tool family
- **WHEN** Gemini auth profiles `work` and `breakglass` already exist
- **AND WHEN** an operator attempts to rename `work` to `breakglass`
- **THEN** the command fails explicitly
- **AND THEN** it does not rename either auth profile
