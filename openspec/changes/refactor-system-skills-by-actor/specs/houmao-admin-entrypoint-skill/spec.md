## ADDED Requirements

### Requirement: Houmao provides a public human-operator entrypoint
Houmao SHALL provide a public skill named `houmao-admin-entrypoint` as the executable entrypoint of the admin pack.

Its startup-visible description and opening workflow SHALL state that the assistant acts for a human operator, is not the managed agent being administered, and routes mutations only after resolving the required target and intent.

#### Scenario: Human invokes the admin entrypoint
- **WHEN** a human invokes `houmao-admin-entrypoint` for a managed-agent operation
- **THEN** the entrypoint establishes an admin actor frame before selecting a protected route
- **AND THEN** it does not use managed self identity as an implicit target

### Requirement: Admin entrypoint resolves target and operation before mutation
For target-sensitive work, the admin entrypoint SHALL resolve the requested operation and explicit project, agent, mailbox, gateway, credential, workspace, or loop target from the prompt and recent unambiguous context.

If a blocking value remains unknown, it SHALL use supported read-only discovery and the required/optional question contract. It SHALL preserve explicit user choices and SHALL NOT guess a mutating target.

#### Scenario: Multiple managed agents match an admin request
- **WHEN** read-only discovery finds more than one plausible target and the user did not identify one
- **THEN** the entrypoint asks for the required target and separates optional modifiers
- **AND THEN** it performs no target mutation before the user resolves the ambiguity

### Requirement: Admin entrypoint routes only through its protected admin composition
Operational commands SHALL route from the public admin entrypoint to the admin composition of `houmao-shared-routines` using manifest-declared route member names.

The entrypoint SHALL reject agent-only routes and SHALL NOT instruct the user to invoke a protected logical id as a public skill.

#### Scenario: Admin routes agent inspection
- **WHEN** a human asks to inspect an explicitly selected managed agent
- **THEN** the entrypoint routes through `houmao-admin-entrypoint->houmao-shared-routines->agent-inspect`
- **AND THEN** the protected routine receives the admin frame and selected target

### Requirement: Admin entrypoint delegates welcome-oriented commands
Empty invocation and the commands `help`, `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour` SHALL delegate to the installed public `houmao-admin-welcome` skill.

The entrypoint SHALL preserve supplied context during delegation and SHALL NOT maintain a second copy of the welcome content beneath its own asset tree.

#### Scenario: Empty admin invocation opens welcome guidance
- **WHEN** a user invokes `houmao-admin-entrypoint` without an executable operation
- **THEN** the entrypoint routes to `houmao-admin-welcome`
- **AND THEN** the response stays read-only until the user requests a concrete handoff

### Requirement: Admin entrypoint owns explicit joined-session adoption handoff
The admin entrypoint SHALL route joined-session adoption only when the human explicitly asks to adopt the current session.

After successful adoption it SHALL stop admin routing, refresh skill discovery when necessary, verify managed self identity, and hand later work to `houmao-agent-entrypoint`.

#### Scenario: Adoption succeeds
- **WHEN** the explicit joined-session adoption command succeeds
- **THEN** the admin entrypoint reports the actor transition
- **AND THEN** subsequent managed self work enters through `houmao-agent-entrypoint`

