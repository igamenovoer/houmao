## ADDED Requirements

### Requirement: `project easy profile create` supports stored managed-header policy
`houmao-mgr project easy profile create` SHALL accept:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, the created easy profile SHALL store managed-header policy `inherit`.

`project easy profile get --name <profile>` SHALL report the stored managed-header policy.

#### Scenario: Easy profile create stores disabled managed-header policy
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --no-managed-header`
- **THEN** the created easy profile stores managed-header policy `disabled`
- **AND THEN** later `project easy profile get --name reviewer-fast` reports that stored policy

### Requirement: `project easy instance launch` supports one-shot managed-header override
`houmao-mgr project easy instance launch` SHALL accept:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, easy-instance launch SHALL inherit managed-header policy from the selected easy profile when one is present, otherwise from the system default.

Direct one-shot managed-header override SHALL NOT rewrite the stored easy profile.

#### Scenario: Easy-instance launch disables the managed header for one profile-backed launch
- **WHEN** easy profile `reviewer-fast` stores managed-header policy `enabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** easy profile `reviewer-fast` still records managed-header policy `enabled`

#### Scenario: Easy-instance launch enables the managed header despite stored disabled policy
- **WHEN** easy profile `reviewer-fast` stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header`
- **THEN** the resulting managed launch prepends the managed prompt header
- **AND THEN** easy profile `reviewer-fast` still records managed-header policy `disabled`
