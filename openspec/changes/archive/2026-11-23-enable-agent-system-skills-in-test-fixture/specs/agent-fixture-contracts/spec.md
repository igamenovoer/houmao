# Spec Delta

## ADDED Requirements

### Requirement: Maintained managed-agent fixtures SHALL preserve the managed-launch agent system-skill default

When a maintained fixture prepares a manager-surface managed agent without an explicit system-skill opt-out, it SHALL leave the managed-launch system-skill policy at its default so the complete `agent` pack is installed in the runtime home.

The fixture SHALL NOT pass a system-skill disabling option for that default path. The prepared run metadata SHALL record whether the default pack or an explicit opt-out applies.

#### Scenario: Default managed preparation keeps the agent pack
- **WHEN** a maintainer prepares a manager-surface fixture run without selecting a system-skill opt-out
- **THEN** the generated specialist leaves `launch.system_skills` at the managed default
- **AND THEN** the launched runtime home receives the complete `agent` system-skill pack
- **AND THEN** the prepared run metadata records the default-pack choice

#### Scenario: Default preparation does not record a disabled policy
- **WHEN** a maintainer inspects a default manager-surface fixture run
- **THEN** its generated specialist does not contain `system_skills: {mode: none}`
- **AND THEN** its run metadata does not describe the run as having no Houmao system skills

### Requirement: Maintained managed-agent fixtures SHALL provide an explicit system-skill opt-out

The fixture SHALL provide an explicit opt-out for managed preparation cases that intentionally require a minimal runtime home. When the opt-out is selected, the fixture SHALL create the specialist with the disabling policy and SHALL record that choice in the prepared run metadata.

#### Scenario: Explicit opt-out prepares a minimal home
- **WHEN** a maintainer prepares a manager-surface fixture run with the system-skill opt-out
- **THEN** the generated specialist records `launch.system_skills.mode` as `none`
- **AND THEN** the prepared run metadata records the opt-out choice

#### Scenario: Opt-out documentation is discoverable
- **WHEN** a maintainer reads the maintained fixture guidance
- **THEN** it identifies the managed-launch `agent` pack as the default
- **AND THEN** it explains the explicit opt-out and when to use it
