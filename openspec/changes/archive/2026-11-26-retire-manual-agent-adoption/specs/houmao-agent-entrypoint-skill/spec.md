# Spec Delta

## MODIFIED Requirements

### Requirement: Houmao provides a public managed-agent entrypoint
Houmao SHALL provide a public skill named `houmao-agent-entrypoint` as the sole public member of the agent pack.

Its startup-visible description and opening workflow SHALL state that the caller is the managed Houmao agent attached to the current session and that substantive routes require verified self identity.

#### Scenario: Managed launch installs the public agent entrypoint
- **WHEN** Houmao builds a managed tool home with default system skills enabled
- **THEN** the home receives the agent pack and public `houmao-agent-entrypoint`
- **AND THEN** it does not receive the admin welcome or admin entrypoint by default
