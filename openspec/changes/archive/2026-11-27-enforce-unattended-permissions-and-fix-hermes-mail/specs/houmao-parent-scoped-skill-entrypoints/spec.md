# Spec Delta

## MODIFIED Requirements

### Requirement: Generated prompts invoke only public skill entrypoints
Automatically generated mailbox-operation and mail-notifier prompts SHALL invoke the eligible public entrypoint through the current tool's native skill syntax. They SHALL describe protected routines as parent-controlled routes and SHALL NOT instruct the agent to discover, open, or invoke a protected entrypoint independently.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Internal object-style route traces MAY appear for diagnostics, but SHALL NOT replace the public `$houmao-agent-entrypoint <route> ...`, `/houmao-agent-entrypoint <route> ...`, or equivalent plain invocation.

#### Scenario: Codex receives a notifier prompt
- **WHEN** the managed agent pack is installed and the gateway generates a Codex mail-notifier prompt
- **THEN** the prompt invokes `$houmao-agent-entrypoint process-emails-via-gateway <gateway-url>`
- **AND THEN** the prompt states that the public entrypoint controls protected traversal
- **AND THEN** the prompt does not present a protected file or logical id as a standalone native skill trigger

#### Scenario: Hermes receives routed mailbox guidance

- **WHEN** both public siblings are installed and Houmao generates mailbox guidance for a managed Hermes session
- **THEN** it tells Hermes to call `skill_view` for `houmao-agent-entrypoint` and provides the operation's mailbox route
- **AND THEN** the public entrypoint verifies self before delegating with the current actor and mailbox context to `houmao-shared-routines`
- **AND THEN** only that sibling selects and loads the protected child, without asking Hermes to look up or manage the child as a public skill

#### Scenario: Agent pack is unavailable
- **WHEN** the gateway cannot find the public managed-agent entrypoint
- **THEN** the generated prompt uses the supported mailbox API fallback
- **AND THEN** it does not claim that protected mailbox routines are installed
