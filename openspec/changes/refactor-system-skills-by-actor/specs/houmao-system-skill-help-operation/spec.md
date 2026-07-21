## ADDED Requirements

### Requirement: Public system skills handle help before operational routing
Each current public Houmao system skill SHALL expose read-only help from its top-level `SKILL.md` and SHALL answer explicit help intent before identity verification, target collection, protected routing, command execution, or mutation.

`houmao-admin-welcome` SHALL own first-use and route-comparison help. `houmao-admin-entrypoint` SHALL delegate empty and welcome-oriented help to that public sibling. `houmao-agent-entrypoint` SHALL provide concise help for its eligible managed-agent routes without claiming an agent welcome.

#### Scenario: Admin entrypoint receives explicit help
- **WHEN** a user invokes `houmao-admin-entrypoint help`
- **THEN** the entrypoint delegates to `houmao-admin-welcome`
- **AND THEN** neither public skill executes a protected operation or asks for an operational target

#### Scenario: Agent entrypoint receives explicit help
- **WHEN** a user invokes `houmao-agent-entrypoint help`
- **THEN** it lists the managed-agent routes and identity prerequisite concisely
- **AND THEN** it does not perform a substantive self-identity or state operation solely to answer help

### Requirement: Help distinguishes public invocations from protected routes
Public help SHALL list copyable prompts that begin with `$houmao-admin-welcome`, `$houmao-admin-entrypoint`, or `$houmao-agent-entrypoint`.

It MAY show entrypoint-qualified protected designators to explain routing, but SHALL identify them as internal route traces and SHALL NOT present protected logical ids as independently invokable top-level skills.

#### Scenario: Help describes agent inspection
- **WHEN** public help explains the protected inspect capability
- **THEN** it provides a public entrypoint invocation the user can copy
- **AND THEN** any protected designator is labeled as a nested route rather than an install or public trigger

### Requirement: Protected routers expose read-only route summaries
Each protected `SKILL.md` SHALL provide enough read-only help for its parent to summarize purpose, available commands, eligible actors, out-of-scope work, and direct child routes.

Protected help SHALL run only within a valid actor frame or fail closed to the eligible public entrypoints. It SHALL be checked before a protected command's default operational behavior.

#### Scenario: Protected loop help lacks required loop directory
- **WHEN** a valid entrypoint route requests help for a protected loop routine without a loop directory
- **THEN** the routine returns its command summary
- **AND THEN** it does not treat the request as initialization or ask for the loop directory

### Requirement: Content validation enforces public help and protected route summaries
Manifest-aware tests SHALL require help coverage for every public skill and route-summary coverage for every protected router and direct subskill.

The validator SHALL check public command-map completeness, eligible-actor wording, parent “When to Route Here” summaries, and the absence of direct protected invocation examples.

#### Scenario: New protected subskill lacks a parent summary
- **WHEN** a maintainer adds a protected subskill without a matching parent route summary
- **THEN** system-skill content validation fails
- **AND THEN** the pack cannot pass recursive staging validation

## REMOVED Requirements

### Requirement: Current system skills expose a read-only help operation
**Reason**: Current install units are public pack skills, while protected routines use nested route summaries.
**Migration**: Put top-level help on the three public skills and protected help behind a valid actor frame.

### Requirement: Help responses show available functionality
**Reason**: Help must now distinguish public invocations from protected implementation.
**Migration**: Use the public and protected help contracts in this delta.

### Requirement: Operation-heavy skills list help beside operations
**Reason**: Operation-heavy routines are protected rather than peer top-level skills.
**Migration**: List help in each protected router's command map and check it before default commands.

### Requirement: Router-style skills handle help before page selection
**Reason**: Router behavior now spans public entrypoints and nested protected routers.
**Migration**: Apply help-first routing recursively through the actor-qualified route.

### Requirement: Future current skills include the help operation
**Reason**: Future validation must distinguish public skills, protected mounts, and protected subskills.
**Migration**: Enforce role-appropriate help and route-summary requirements through the manifest-aware validator.

