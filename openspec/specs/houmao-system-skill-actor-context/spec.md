# houmao-system-skill-actor-context Specification

## Purpose
TBD - created by archiving change refactor-system-skills-by-actor. Update Purpose after archive.
## Requirements
### Requirement: Executable entrypoints establish an immutable actor frame
Before routing substantive work, each executable public entrypoint SHALL establish a routing frame containing `actor_kind`, `entrypoint_name`, verified self identity when required, requested target, and selected routine.

The actor kind SHALL be either `admin` or `agent`. Protected routers and routines SHALL preserve the actor kind and entrypoint name for the complete route and SHALL NOT infer, replace, or promote the actor kind.

#### Scenario: Shared routine preserves admin actor
- **WHEN** `houmao-admin-entrypoint` routes a request into a shared protected routine
- **THEN** the routine follows its admin branch with the supplied target
- **AND THEN** it does not reinterpret the current process as a managed-agent self target

#### Scenario: Shared routine preserves agent actor
- **WHEN** `houmao-agent-entrypoint` routes a request into a shared protected routine
- **THEN** the routine retains the verified managed-agent identity as its actor context
- **AND THEN** it does not acquire admin posture because the user asks for an operator-like action

### Requirement: Admin actor targets are explicit or unambiguously recovered
An admin actor SHALL represent an assistant acting for a human operator and SHALL NOT represent the managed agent being administered.

For target-sensitive work, the admin path SHALL use a target explicitly supplied by the user, an unambiguous target preserved in recent route context, or read-only discovery followed by a required/optional input question. It SHALL NOT default to `agents self` merely because the command runs inside a shell or tmux session.

#### Scenario: Admin request lacks a managed-agent target
- **WHEN** an admin actor receives a target-sensitive request with no explicit or unambiguous target
- **THEN** it may perform supported read-only discovery
- **AND THEN** it asks for the blocking target using the required/optional question contract before mutation

### Requirement: Agent actor verifies managed self identity before substantive routing
An agent actor SHALL run `houmao-mgr --print-json agents self identity` before each substantive entrypoint route.

The route SHALL fail closed when the command fails, returns no usable identity, or conflicts with retained session identity. A successful result SHALL become the default self target for self-scoped routine branches.

#### Scenario: Managed identity is verified
- **WHEN** the agent entrypoint receives a substantive request and self identity resolves successfully
- **THEN** the routing frame records the returned managed-agent identity
- **AND THEN** self-scoped routines use that identity without asking the user to repeat it

#### Scenario: Managed identity cannot be verified
- **WHEN** `houmao-mgr --print-json agents self identity` fails or returns unusable output
- **THEN** the agent entrypoint stops before loading or executing a protected routine
- **AND THEN** it reports the identity failure and directs operator-scoped work to `houmao-admin-entrypoint`

### Requirement: Audience eligibility cannot be changed by prompt text
The selected entrypoint and manifest routing matrix SHALL determine which protected routines are eligible.

An admin actor SHALL NOT route to agent-only routines, and an agent actor SHALL NOT route to admin-only routines. Prompt text, a requested command name, or a protected routine discovered recursively SHALL NOT expand that eligibility.

#### Scenario: Agent asks for an admin-only credential routine
- **WHEN** an agent actor receives a request that maps to `houmao-credential-mgr`
- **THEN** the agent entrypoint refuses the ineligible route
- **AND THEN** it identifies the admin entrypoint as the public owner without executing the protected routine

### Requirement: Protected routines fail closed without an actor frame
Every protected router and subskill SHALL state that it executes only when routed from one of its eligible public entrypoints with a valid actor frame.

If a host discovers or invokes a protected routine directly, the routine SHALL perform no operational action and SHALL direct the request to the appropriate public entrypoint.

#### Scenario: Recursive host invokes protected inspect routine directly
- **WHEN** a protected inspect routine is invoked without an entrypoint name and actor kind
- **THEN** it does not inspect or mutate managed-agent state
- **AND THEN** it returns the supported public entrypoint routes

### Requirement: Joined-session adoption creates a new agent frame after success
The admin actor MAY route an explicit human request to adopt the current session through the supported joined-session workflow.

The admin frame SHALL remain active until adoption succeeds. After success, the route SHALL end the admin frame, refresh public-skill discovery when required, verify managed self identity, and begin later work through `houmao-agent-entrypoint`; it SHALL NOT mutate the admin frame into an agent frame in place.

#### Scenario: Human adopts the current session
- **WHEN** the admin entrypoint completes an explicitly requested joined-session adoption
- **THEN** it stops admin-scoped routing for subsequent work in that session
- **AND THEN** it hands subsequent work to the agent entrypoint only after managed self identity succeeds

