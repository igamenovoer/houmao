## ADDED Requirements

### Requirement: Human-operator entrypoint establishes admin posture before sibling routing
`houmao-admin-entrypoint` SHALL declare that the executing assistant acts for a human operator and is not the managed agent being administered. It SHALL resolve target-sensitive work from an explicit target or unambiguous user-provided context and SHALL NOT default to managed self.

After route selection, ordinary system work SHALL delegate to the installed `houmao-shared-routines` sibling with an immutable admin frame. Pro and lite loop work SHALL delegate directly to the corresponding top-level loop sibling.

#### Scenario: Operator requests agent inspection
- **WHEN** a human invokes `$houmao-admin-entrypoint agent-inspect discover` with an explicit target
- **THEN** the entrypoint establishes an admin frame
- **AND THEN** it delegates the request to the agent-inspect child owned by `houmao-shared-routines`
- **AND THEN** it does not read a local entrypoint subskill path

#### Scenario: Operator requests a pro loop
- **WHEN** a human invokes the admin entrypoint's pro-loop route
- **THEN** the entrypoint passes its admin frame to `houmao-agent-loop-pro`
- **AND THEN** shared routines do not own or duplicate the loop skill

### Requirement: Managed-agent entrypoint verifies self before sibling routing
`houmao-agent-entrypoint` SHALL run `houmao-mgr --print-json agents self identity` before every substantive route. Empty, malformed, failed, unverified, or context-mismatched identity evidence SHALL stop the route.

After successful verification, eligible ordinary work SHALL delegate to `houmao-shared-routines` with an immutable agent frame and verified self identity. Eligible loop work SHALL delegate directly to a top-level loop sibling with the same frame.

#### Scenario: Verified managed agent reads its mailbox
- **WHEN** the agent entrypoint receives an ordinary mailbox request and self identity verifies
- **THEN** it delegates to the shared agent-email-comms child with verified self as the default target
- **AND THEN** it retains the managed-agent actor throughout the route

#### Scenario: Managed identity cannot be established
- **WHEN** the required self-identity command fails or returns invalid evidence
- **THEN** the entrypoint reports that managed identity cannot be verified
- **AND THEN** it does not invoke shared routines or a loop sibling

### Requirement: Entrypoints expose complete static route indexes
Each actor entrypoint SHALL use a collection-of-routines subcommand table that lists every eligible route argument, one distinguishing `When to Route Here` sentence, and its sibling delegation target.

The admin entrypoint SHALL list admin-only and shared routes, the specialist compatibility alias, and both loop routes. The agent entrypoint SHALL list agent-only and shared routes plus both loop routes. Ineligible routes SHALL remain explicit rejections and SHALL NOT become eligible from prompt text.

#### Scenario: User asks entrypoint help
- **WHEN** a user requests help from either actor entrypoint
- **THEN** the response lists that entrypoint's complete eligible route surface and sibling destinations
- **AND THEN** it does not present shared children as local entrypoint subskills

### Requirement: Shared routines support direct advanced invocation
`houmao-shared-routines` SHALL be directly invokable as a public skill. Direct invocation SHALL default to human-operator posture and SHALL support an explicit leading `as-agent` qualifier that performs fresh managed-self verification.

Direct invocation SHALL bypass only actor-entrypoint route selection. It SHALL retain child eligibility, required-target questions, managed-self verification, command validation, operation guardrails, and runtime authorization.

#### Scenario: Advanced user invokes a shared routine directly
- **WHEN** a user invokes `$houmao-shared-routines agent-inspect discover` without an inherited frame
- **THEN** shared routines establishes admin posture
- **AND THEN** it loads only `subskills/houmao-agent-inspect/SKILL-MAIN.md` and the resources required for discovery

#### Scenario: Direct caller explicitly selects managed self
- **WHEN** a caller invokes shared routines with the leading `as-agent` qualifier
- **THEN** shared routines performs the same fresh self-identity verification as the agent entrypoint
- **AND THEN** it stops before child loading when verification fails

### Requirement: Shared routines selectively load owned children
The shared root SHALL list all sixteen direct children with one substantive `When to Route Here` sentence per child. After selecting one child, it SHALL explicitly load only that child's `SKILL-MAIN.md` and required owned resources.

Shared routines SHALL route loop-shaped work to the top-level pro or lite sibling. It SHALL NOT claim either loop as a child.

#### Scenario: Shared route selects workspace management
- **WHEN** the selected route is workspace management
- **THEN** the parent loads `subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md`
- **AND THEN** it does not scan or preload sibling child entrypoints

### Requirement: Top-level loop skills accept direct and inherited actor posture
`houmao-agent-loop-pro` and `houmao-agent-loop-lite` SHALL remain manually invokable with their original skill names and operations. Direct invocation SHALL default to admin posture, explicit `as-agent` invocation SHALL verify managed self, and actor-entrypoint invocation SHALL preserve its inherited frame.

No-operation invocation SHALL retain the original `init` default and missing-`<loop-dir>` blocker. Generic loop wording SHALL NOT implicitly select pro or lite.

#### Scenario: User directly invokes lite without an operation
- **WHEN** a user invokes `$houmao-agent-loop-lite` with no operation or task
- **THEN** the skill selects `init` under admin posture
- **AND THEN** it asks for `<loop-dir>` before creating files

### Requirement: Admin welcome remains an independent read-only sibling
`houmao-admin-welcome` SHALL own first-use orientation, route comparison, state-aware path selection, and guided touring. It SHALL NOT own shared routines or execute mutating system work.

An actionable request SHALL hand the complete selected context to `houmao-admin-entrypoint`. Empty or welcome-style admin-entrypoint requests SHALL delegate to the welcome sibling.

#### Scenario: First-time user starts a guided tour
- **WHEN** welcome finds no Houmao project overlay
- **THEN** it presents Create Houmao Project, Subsystem Exploration, and Inspect as the only no-prompt choices
- **AND THEN** it does not execute project creation

### Requirement: Actor routing is not an authorization boundary
All sibling and child routes SHALL describe actor posture as routing context. Runtime CLI and service validation SHALL remain authoritative for permissions, target validity, and side effects.

#### Scenario: Skill text names an otherwise invalid target
- **WHEN** a routed operation reaches a runtime surface with an unauthorized or invalid target
- **THEN** the runtime surface rejects the operation according to its own contract
- **AND THEN** public skill placement does not override that rejection
