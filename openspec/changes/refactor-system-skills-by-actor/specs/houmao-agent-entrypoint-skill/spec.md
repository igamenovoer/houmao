## ADDED Requirements

### Requirement: Houmao provides a public managed-agent entrypoint
Houmao SHALL provide a public skill named `houmao-agent-entrypoint` as the sole public member of the agent pack.

Its startup-visible description and opening workflow SHALL state that the caller is the managed Houmao agent attached to the current session and that substantive routes require verified self identity.

#### Scenario: Managed launch installs the public agent entrypoint
- **WHEN** Houmao builds or joins a managed tool home with default system skills enabled
- **THEN** the home receives the agent pack and public `houmao-agent-entrypoint`
- **AND THEN** it does not receive the admin welcome or admin entrypoint by default

### Requirement: Agent entrypoint verifies identity for every substantive route
Before selecting a protected operational route, the agent entrypoint SHALL run `houmao-mgr --print-json agents self identity`, validate the returned identity, and record it in the agent actor frame.

Help that only explains the entrypoint MAY remain read-only without identity resolution. All state inspection, communication, mailbox, gateway, lifecycle, workspace, loop, memory, and interop routes SHALL require verification.

#### Scenario: Identity check precedes mailbox route
- **WHEN** a managed agent receives a mailbox task through the agent entrypoint
- **THEN** the entrypoint verifies self identity before loading the protected mailbox routine
- **AND THEN** the protected route receives the verified identity

#### Scenario: Identity failure blocks operation
- **WHEN** self identity cannot be resolved
- **THEN** the entrypoint performs no protected operational route
- **AND THEN** it reports a fail-closed identity diagnostic

### Requirement: Agent entrypoint preserves self scope and explicit cross-agent targets
The verified managed identity SHALL be the default target for self-scoped routes.

When an eligible routine supports communication or control of another agent, the route SHALL require an explicit other-agent target and SHALL retain `actor_kind = agent`. The entrypoint SHALL NOT turn an agent into an admin actor or expose admin-only routine paths.

#### Scenario: Managed agent inspects itself
- **WHEN** the agent asks for its own current state
- **THEN** the entrypoint uses the verified self identity without asking for an agent selector
- **AND THEN** it follows the self branch of the protected inspect routine

#### Scenario: Managed agent messages another agent
- **WHEN** the user explicitly asks the managed agent to message a named peer through an eligible route
- **THEN** the frame records the peer as the operation target while retaining the caller's verified agent identity
- **AND THEN** the route does not acquire admin-only capabilities

### Requirement: Agent entrypoint exposes no guided welcome surface
The agent entrypoint SHALL provide concise route help for its own eligible operations but SHALL NOT install, delegate to, or imply an agent welcome sibling in this change.

Orientation intended for a human operator SHALL identify the admin pack rather than loading admin guidance into the managed-agent actor frame.

#### Scenario: Agent receives first-user tour request
- **WHEN** a request through the agent entrypoint asks for the human operator guided tour
- **THEN** the entrypoint identifies `houmao-admin-welcome` as part of the separately installed admin pack
- **AND THEN** it does not switch actor or execute the tour inside the agent route

