## ADDED Requirements

### Requirement: Project launch profiles store managed-header section policy
`houmao-mgr project agents launch-profiles add` and `houmao-mgr project agents launch-profiles set` SHALL accept repeatable managed-header section policy options using `--managed-header-section SECTION=STATE`.

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

`houmao-mgr project agents launch-profiles set` SHALL also accept:

- `--clear-managed-header-section SECTION` to remove one stored section policy entry,
- `--clear-managed-header-sections` to remove all stored section policy entries.

Whole-header policy SHALL remain controlled by existing `--managed-header`, `--no-managed-header`, and `--clear-managed-header` behavior.

#### Scenario: Launch profile add stores disabled automation notice
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer --managed-header-section automation-notice=disabled`
- **THEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND THEN** omitted identity and Houmao runtime guidance section policy remain inherited default-enabled values
- **AND THEN** omitted task reminder and mail acknowledgement section policy remain inherited default-disabled

#### Scenario: Launch profile set clears one section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled` and identity section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header-section identity`
- **THEN** launch profile `alice` no longer stores an identity section policy
- **AND THEN** launch profile `alice` still stores automation notice section policy `disabled`

#### Scenario: Launch profile set clears all section policies
- **WHEN** launch profile `alice` stores one or more managed-header section policies
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header-sections`
- **THEN** launch profile `alice` no longer stores managed-header section policy entries
- **AND THEN** future launches from `alice` use section-default policy when the whole managed header is enabled

#### Scenario: Launch profile get reports stored section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name alice`
- **THEN** the structured output reports the stored automation notice section policy
- **AND THEN** the output does not report omitted section-default policies as stored values

#### Scenario: Launch profile add enables default-off mail acknowledgement
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name mailer --recipe reviewer --managed-header-section mail-ack=enabled`
- **THEN** launch profile `mailer` stores mail acknowledgement section policy `enabled`
- **AND THEN** future launches from `mailer` include the mail acknowledgement section when the whole managed header resolves to enabled
