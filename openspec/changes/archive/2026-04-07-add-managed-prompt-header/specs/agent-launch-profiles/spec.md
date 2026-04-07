## ADDED Requirements

### Requirement: Launch profiles may store managed-header policy
The shared launch-profile object family SHALL support one optional managed-header policy as reusable birth-time launch configuration.

That stored policy SHALL support:
- `inherit`,
- `enabled`,
- `disabled`.

Launch-profile inspection payloads SHALL report the stored managed-header policy when it is present, and SHALL distinguish explicit `inherit` from an absent unsupported field.

#### Scenario: Explicit launch profile stores disabled managed-header policy
- **WHEN** an operator creates one reusable launch profile with managed-header policy `disabled`
- **THEN** the shared launch-profile object stores that policy as birth-time launch configuration
- **AND THEN** later inspection of that launch profile reports managed-header policy `disabled`

#### Scenario: Easy profile stores inherit managed-header policy
- **WHEN** an operator creates one easy profile without forcing managed-header enabled or disabled
- **THEN** the shared launch-profile object records managed-header policy `inherit`
- **AND THEN** later launch resolution can still fall through to the system default for that field
