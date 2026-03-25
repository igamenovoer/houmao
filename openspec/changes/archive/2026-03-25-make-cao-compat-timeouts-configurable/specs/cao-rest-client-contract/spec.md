## ADDED Requirements

### Requirement: CAO REST client exposes overrideable operational timeout budgets
The system SHALL expose supported operational timeout configuration for the repo-owned CAO-compatible REST client rather than relying on one unoverrideable flat timeout budget for every request.

At minimum, the client contract SHALL distinguish between:

- a general request timeout budget
- a create-operation timeout budget

The default general request timeout SHALL be 15 seconds.

The default create-operation timeout SHALL be 75 seconds.

The create-operation timeout SHALL apply to:

- `POST /sessions`
- `POST /sessions/{session_name}/terminals`

Other client requests SHALL continue using the general request timeout unless a later change defines a more specific budget.

Direct Python callers SHALL be able to override both budgets through supported client construction or call configuration without patching repository source.

#### Scenario: Default client uses split timeout budgets
- **WHEN** a caller uses the default CAO-compatible client configuration
- **THEN** lightweight requests such as health, list, detail, input, output, and delete use a 15-second timeout budget
- **AND THEN** session and terminal creation requests use a 75-second timeout budget

#### Scenario: Explicit client override changes create budget without widening other requests
- **WHEN** a caller constructs the CAO-compatible client with `timeout_seconds = 5` and `create_timeout_seconds = 90`
- **THEN** lightweight requests use a 5-second timeout budget
- **AND THEN** `create_session()` and `create_terminal()` use a 90-second timeout budget
