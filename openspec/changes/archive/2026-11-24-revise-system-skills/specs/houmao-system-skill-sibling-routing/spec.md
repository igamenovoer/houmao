# System-Skill Sibling Routing Delta

## MODIFIED Requirements

### Requirement: Entrypoints expose complete static route indexes
Each actor entrypoint SHALL use a collection-of-routines subcommand table that lists every eligible route argument, one distinguishing “When to Route Here” sentence, and its sibling delegation target.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The admin entrypoint SHALL list admin-only and shared routes, the specialist compatibility alias, and both loop routes. The agent entrypoint SHALL list agent-only and shared routes plus both loop routes. Ineligible routes SHALL remain explicit rejections and SHALL NOT become eligible from prompt text.

#### Scenario: User asks entrypoint help
- **WHEN** a user requests help from either actor entrypoint
- **THEN** the response lists that entrypoint's complete eligible route surface, including `agent-access` and `agent-files`, and names its sibling destinations
- **AND THEN** it does not present shared children as local entrypoint subskills

### Requirement: Shared routines selectively load owned children
The shared root SHALL list every manifest-declared direct child with one substantive “When to Route Here” sentence. After selection it SHALL explicitly load only the chosen child's `SKILL-MAIN.md` and necessary owned resources.

Shared routines SHALL route loop-shaped work to the top-level Pro or Lite sibling.

#### Scenario: Shared route selects workspace management
- **WHEN** the selected route is workspace management
- **THEN** the parent loads `subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md`
- **AND THEN** it does not scan or preload sibling child entrypoints

#### Scenario: Shared route selects versioned file edits
- **WHEN** an actor entrypoint hands off a request to edit a peer's versioned files
- **THEN** shared routines passes the existing actor frame to its `houmao-agent-files` child
- **AND THEN** the child uses the selected target and existing gateway authorization

### Requirement: Admin welcome remains an independent read-only sibling
`houmao-admin-welcome` SHALL own first-use orientation, route comparison, state-aware path selection, and guided touring. It SHALL remain manual and read-only. Once invoked, it SHALL hand actionable requests and their selected context to `houmao-admin-entrypoint`.

#### Scenario: First-time user starts a guided tour
- **WHEN** welcome finds no Houmao project overlay after manual invocation
- **THEN** it presents Create Houmao Project, Subsystem Exploration, and Inspect as the only no-prompt choices
- **AND THEN** it does not execute project creation

#### Scenario: Empty or welcome-style admin invocation
- **WHEN** a user invokes the admin entrypoint without an action or asks for orientation
- **THEN** the admin entrypoint returns local read-only guidance and may recommend the exact manual welcome invocation
