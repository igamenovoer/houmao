# Spec Delta

## MODIFIED Requirements

### Requirement: Entrypoints classify intent before operational gates
After invocation, each actor entrypoint SHALL classify the request as informational, operational, unrelated, unsupported, or an explicitly selected downstream route before target discovery, sibling loading, or operational command execution.

Informational requests SHALL be answered locally and read-only. They SHALL NOT perform target discovery or load shared routines or a loop sibling. Agent informational requests SHALL NOT run managed-self identity verification.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For operational requests, the admin entrypoint SHALL establish its immutable admin frame before substantive routing. The agent entrypoint SHALL run exactly `houmao-mgr --print-json agents self identity`, validate fresh context-matching evidence, and fail closed before selecting or delegating a substantive route when verification fails.

After the actor gate, the entrypoint SHALL select exactly one eligible route, resolve required inputs and targets, delegate with the immutable handoff frame when needed, and report the outcome.

#### Scenario: Managed agent asks an informational question
- **WHEN** a managed agent naturally asks what Houmao capabilities are available to it
- **THEN** the agent entrypoint returns local read-only information
- **AND THEN** it does not run the self-identity command or load a sibling

#### Scenario: Managed agent requests an operational self route
- **WHEN** a managed agent naturally requests eligible Houmao work on itself
- **THEN** the agent entrypoint classifies the request as operational
- **AND THEN** it performs fresh self-identity verification before substantive route selection or delegation

#### Scenario: Operational identity verification fails
- **WHEN** the exact self-identity command fails or returns invalid, unverified, stale, or context-mismatched evidence
- **THEN** the agent entrypoint stops before sibling loading or operational execution
- **AND THEN** it reports that managed identity cannot be verified

#### Scenario: Operational request lacks a required target
- **WHEN** an activated entrypoint selects an eligible target-sensitive route but cannot resolve its required target safely
- **THEN** it asks one focused target question rather than guessing or invoking the sibling prematurely

### Requirement: Deployment selects the actor pack independently of activation
Explicit operator installation without a pack override SHALL continue to select the admin pack. Managed launch SHALL continue to select the agent pack by default.

The admin pack SHALL contain admin welcome, admin entrypoint, shared routines, and both loop siblings. The agent pack SHALL contain agent entrypoint, shared routines, and both loop siblings, and SHALL NOT contain admin welcome or admin entrypoint.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Changing activation posture MUST NOT dynamically compose skill content, alter static copy or symlink projection, or inject the admin entrypoint into a managed-agent home.

#### Scenario: Operator manually installs the default surface
- **WHEN** a user runs the supported system-skill installer without an explicit pack override
- **THEN** the installer selects the admin pack
- **AND THEN** that selection occurs only because the user invoked installation

#### Scenario: Houmao constructs a managed home
- **WHEN** managed launch performs default system-skill installation
- **THEN** it installs the agent pack and not the admin pack
- **AND THEN** the managed agent receives `houmao-agent-entrypoint` as its only actor entrypoint

#### Scenario: Static skills are installed after the policy change
- **WHEN** either actor pack is copied, symlinked, or installed through a standard Skills CLI selection
- **THEN** every selected skill remains a complete checked-in static directory
- **AND THEN** no runtime-composed entrypoint or subskill tree is generated
