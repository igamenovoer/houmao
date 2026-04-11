## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header section overrides
`houmao-mgr agents launch` SHALL accept repeatable one-shot managed-header section overrides using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

When neither `--managed-header-section` nor whole-header `--managed-header` / `--no-managed-header` is supplied, `agents launch` SHALL inherit managed-header section policy from the selected launch profile when one is present, otherwise from the section default.

Direct one-shot managed-header section overrides SHALL influence only the current launch and SHALL NOT rewrite stored launch-profile state.

If the whole managed header resolves to disabled, section-level overrides SHALL NOT render managed-header sections for that launch.

#### Scenario: Direct launch disables only automation notice for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section automation-notice=disabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the identity and Houmao runtime guidance sections
- **AND THEN** the resulting managed launch does not include the automation notice section

#### Scenario: Direct section override does not rewrite launch profile
- **WHEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** stored launch profile `alice` still records automation notice section policy `disabled`

#### Scenario: Direct launch enables mail acknowledgement for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section mail-ack=enabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the mail acknowledgement section
- **AND THEN** the resulting managed launch does not rewrite stored launch-profile state

#### Scenario: Whole-header disable still wins over direct section enable
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --no-managed-header --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch does not include `<managed_header>`
- **AND THEN** the automation notice section does not render

#### Scenario: Invalid section override fails before launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section typo=enabled`
- **THEN** the command fails before provider launch
- **AND THEN** the error identifies `typo` as an unsupported managed-header section name
