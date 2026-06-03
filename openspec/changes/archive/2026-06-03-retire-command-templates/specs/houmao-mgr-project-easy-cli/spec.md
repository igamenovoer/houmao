## MODIFIED Requirements

### Requirement: Project profile replaces easy profile terminology
The user-facing term `easy profile` SHALL be replaced by `profile` in ordinary project commands, documentation, config drafts, and packaged system skills.

Internal persisted lane names MAY remain stable during migration when changing them would create unnecessary catalog churn, but user-facing output SHALL explain the resource as a project profile.

#### Scenario: Profile get reports project profile terminology
- **WHEN** an operator runs `houmao-mgr project profile get --name reviewer-fast`
- **THEN** the command reports the resource as a project profile
- **AND THEN** it does not call the resource an easy profile in ordinary user-facing fields

## REMOVED Requirements

### Requirement: `project` authoring surfaces provide command-template entries
**Reason**: Project command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr project specialist ...`, `houmao-mgr project profile ...`, and `houmao-mgr project agents launch ...` commands. Use `internals config-drafts generate` only for supported YAML draft documents.

#### Scenario: Project authoring is direct
- **WHEN** a skill documents project specialist, profile, or launch actions
- **THEN** it shows direct `houmao-mgr project ...` commands rather than command-template ids

### Requirement: `project` templates preserve launch default omission
**Reason**: Launch default omission is owned by direct command usage and command implementations, not by project command templates.
**Migration**: Skills omit optional flags from direct project commands unless the user explicitly requested those values or the selected command requires them.

#### Scenario: Project command optional flags remain explicit
- **WHEN** a user does not request prompt mode or launch posture persistence
- **THEN** the direct project command snippet omits the corresponding optional flags
