## ADDED Requirements

### Requirement: CLI reference documents managed-header section flags
The `houmao-mgr` CLI reference SHALL document managed-header section flags on every CLI surface that supports them.

At minimum, the CLI reference SHALL document:

- `--managed-header-section SECTION=STATE` on `houmao-mgr agents launch`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr project agents launch-profiles add`,
- `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` on `houmao-mgr project agents launch-profiles set`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr project easy profile create`,
- `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` on `houmao-mgr project easy profile set`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr project easy instance launch`.

The CLI reference SHALL list supported section names and states, and SHALL state each section's default, including that `task-reminder` and `mail-ack` default to disabled unless explicitly enabled.

#### Scenario: Reader finds one-shot launch section flags
- **WHEN** a reader opens the CLI reference for `houmao-mgr agents launch`
- **THEN** the reference documents `--managed-header-section SECTION=STATE`
- **AND THEN** the reference describes it as a one-shot launch override that does not rewrite stored launch-profile state

#### Scenario: Reader finds stored launch-profile section flags
- **WHEN** a reader opens the CLI reference for project launch-profile or easy-profile create/set commands
- **THEN** the reference documents `--managed-header-section SECTION=STATE`
- **AND THEN** the reference documents the clear flags available on set commands

#### Scenario: Reader sees supported section vocabulary
- **WHEN** a reader looks at any managed-header section flag description
- **THEN** the reference lists `identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack` as supported sections
- **AND THEN** the reference lists `enabled` and `disabled` as supported states
- **AND THEN** the reference states that `task-reminder` and `mail-ack` default to disabled
