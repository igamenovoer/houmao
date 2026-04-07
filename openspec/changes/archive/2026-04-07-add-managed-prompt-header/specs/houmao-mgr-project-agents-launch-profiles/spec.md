## ADDED Requirements

### Requirement: `project agents launch-profiles` manages explicit launch-profile managed-header policy
`houmao-mgr project agents launch-profiles add` SHALL accept:

- `--managed-header`
- `--no-managed-header`

`houmao-mgr project agents launch-profiles set` SHALL accept:

- `--managed-header`
- `--no-managed-header`
- `--clear-managed-header`

`--managed-header` and `--no-managed-header` SHALL be mutually exclusive on both surfaces.

`--clear-managed-header` SHALL clear the stored explicit policy so the profile returns to `inherit`.

`launch-profiles get --name <profile>` SHALL report the stored managed-header policy.

#### Scenario: Add stores an explicit disabled managed-header policy
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --no-managed-header`
- **THEN** the created explicit launch profile stores managed-header policy `disabled`
- **AND THEN** later `launch-profiles get --name alice` reports that stored policy

#### Scenario: Set clears the stored managed-header policy back to inherit
- **WHEN** explicit launch profile `alice` already stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header`
- **THEN** the stored explicit launch profile returns to managed-header policy `inherit`
- **AND THEN** later launches from `alice` fall back to the system default unless a stronger one-shot override is supplied
