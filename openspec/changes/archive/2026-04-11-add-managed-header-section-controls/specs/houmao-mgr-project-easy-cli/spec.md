## ADDED Requirements

### Requirement: Easy profiles store managed-header section policy
`houmao-mgr project easy profile create` and `houmao-mgr project easy profile set` SHALL accept repeatable managed-header section policy options using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

The stored section policy SHALL apply only to the named section. Omitted sections SHALL inherit the section default.

`houmao-mgr project easy profile set` SHALL also accept:

- `--clear-managed-header-section SECTION` to remove one stored section policy entry,
- `--clear-managed-header-sections` to remove all stored section policy entries.

Whole-header policy SHALL remain controlled by existing `--managed-header`, `--no-managed-header`, and `--clear-managed-header` behavior.

#### Scenario: Easy profile create stores disabled automation notice
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --managed-header-section automation-notice=disabled`
- **THEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND THEN** omitted identity and Houmao runtime guidance section policy remain inherited default-enabled values
- **AND THEN** omitted task reminder and mail acknowledgement section policy remain inherited default-disabled

#### Scenario: Easy profile set clears one section policy
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled` and identity section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-fast --clear-managed-header-section identity`
- **THEN** easy profile `reviewer-fast` no longer stores an identity section policy
- **AND THEN** easy profile `reviewer-fast` still stores automation notice section policy `disabled`

#### Scenario: Easy profile get reports stored section policy
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy profile get --name reviewer-fast`
- **THEN** the structured output reports the stored automation notice section policy
- **AND THEN** the output does not report omitted section-default policies as stored values

#### Scenario: Easy profile create enables default-off mail acknowledgement
- **WHEN** an operator runs `houmao-mgr project easy profile create --name mailer-fast --specialist reviewer --managed-header-section mail-ack=enabled`
- **THEN** easy profile `mailer-fast` stores mail acknowledgement section policy `enabled`
- **AND THEN** future launches from `mailer-fast` include the mail acknowledgement section when the whole managed header resolves to enabled

### Requirement: Easy-instance launch supports one-shot managed-header section overrides
`houmao-mgr project easy instance launch` SHALL accept repeatable one-shot managed-header section overrides using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

When neither `--managed-header-section` nor whole-header `--managed-header` / `--no-managed-header` is supplied, easy-instance launch SHALL inherit managed-header section policy from the selected easy profile when one is present, otherwise from the section default.

Direct one-shot managed-header section overrides SHALL influence only the current launch and SHALL NOT rewrite stored easy-profile state.

If the whole managed header resolves to disabled, section-level overrides SHALL NOT render managed-header sections for that launch.

#### Scenario: Easy-instance launch disables only automation notice for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section automation-notice=disabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the identity and Houmao runtime guidance sections
- **AND THEN** the resulting managed launch does not include the automation notice section

#### Scenario: Easy-instance section override does not rewrite easy profile
- **WHEN** easy profile `reviewer-fast` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** easy profile `reviewer-fast` still records automation notice section policy `disabled`

#### Scenario: Easy-instance launch enables mail acknowledgement for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --managed-header-section mail-ack=enabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the mail acknowledgement section
- **AND THEN** easy profile `reviewer-fast` is not rewritten

#### Scenario: Easy-instance launch includes automation notice for as-is specialist
- **WHEN** specialist `reviewer` stores `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer`
- **AND WHEN** the whole managed header is not disabled
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** `as_is` does not disable agent-facing automation guidance
