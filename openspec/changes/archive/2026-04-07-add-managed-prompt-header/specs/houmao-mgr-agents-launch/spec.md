## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header override
`houmao-mgr agents launch` SHALL accept one-shot managed-header override flags:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, `agents launch` SHALL inherit managed-header policy from the selected launch profile when one is present, otherwise from the system default.

Direct one-shot managed-header override SHALL influence only the current launch and SHALL NOT rewrite stored launch-profile state.

#### Scenario: Direct launch disables the managed header for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** future launches without `--no-managed-header` still fall back to profile or system-default behavior

#### Scenario: Direct disable wins over launch-profile-owned enabled policy
- **WHEN** launch profile `alice` stores managed-header policy `enabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** stored launch profile `alice` still records managed-header policy `enabled`

#### Scenario: Direct enable wins over launch-profile-owned disabled policy
- **WHEN** launch profile `alice` stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --managed-header`
- **THEN** the resulting managed launch prepends the managed prompt header
- **AND THEN** stored launch profile `alice` still records managed-header policy `disabled`
