## ADDED Requirements

### Requirement: Launch-profiles guide documents managed-header section policy
The launch-profiles guide SHALL document that stored launch profiles can persist managed-header section policy independently from whole managed-header policy.

At minimum, the guide SHALL explain:

- `identity`, `houmao-runtime-guidance`, and `automation-notice` default to enabled when the whole managed header is enabled,
- `task-reminder` and `mail-ack` default to disabled unless explicitly enabled,
- whole-header `--no-managed-header` disables every section,
- section-level policy can disable one section such as `automation-notice` while keeping the identity and Houmao runtime guidance sections,
- section-level policy can enable a default-disabled section such as `task-reminder` or `mail-ack`,
- omitted section policy means section default rather than always enabled or disabled,
- direct launch section overrides affect only one launch and do not rewrite stored launch-profile state.

#### Scenario: Reader understands stored section policy
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains how stored managed-header section policy works
- **AND THEN** the guide states that omitted section policy falls back to each section's default
- **AND THEN** the guide states that `task-reminder` and `mail-ack` default disabled unless explicitly enabled

#### Scenario: Reader understands whole-header policy precedence
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains that whole-header disable suppresses all managed-header sections
- **AND THEN** the guide distinguishes whole-header policy from section-level policy

#### Scenario: Reader understands direct override scope
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains that direct launch section overrides affect only the current launch
- **AND THEN** the guide states that direct launch overrides do not rewrite stored profile policy
