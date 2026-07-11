## ADDED Requirements

### Requirement: Project-easy commands exclude Gemini
Project specialist, profile, and agent commands SHALL NOT accept Gemini as a tool or launch lane.

#### Scenario: Gemini specialist creation is unavailable
- **WHEN** an operator supplies `--tool gemini` to `houmao-mgr project specialist create`
- **THEN** command parsing rejects the unsupported tool
- **AND THEN** no Gemini specialist, credential, recipe, or profile is persisted

## REMOVED Requirements

### Requirement: Gemini specialists default to unattended headless launch posture
**Reason**: Gemini specialists and managed launches are no longer supported.
**Migration**: Not applicable; no next-release user depends on this provider.
