# houmao-system-skill-entrypoint-activation Specification

## Purpose
TBD - created by archiving change enable-entrypoint-implicit-invocation. Update Purpose after archive.
## Requirements
### Requirement: Explicit skill handles take precedence over implicit discovery
When a prompt contains an explicit installed `$houmao-*` skill handle, the host SHALL select that named skill rather than substituting an actor entrypoint through implicit discovery.

Without an explicit skill handle, a request SHALL be Houmao-related when its subject or requested outcome requires Houmao domain knowledge, explanation, state, routing, or action. Houmao-related requests SHALL include informational questions, command or route learning, incomplete tasks, and executable operations. An incidental occurrence of the word `Houmao` in otherwise unrelated material MUST NOT by itself satisfy this trigger.

#### Scenario: User explicitly invokes a manual root
- **WHEN** a caller submits `$houmao-admin-welcome ...`, `$houmao-shared-routines ...`, `$houmao-agent-loop-pro ...`, or `$houmao-agent-loop-lite ...`
- **THEN** the named installed root is selected directly
- **AND THEN** an actor entrypoint is not substituted as the initial root

#### Scenario: Unrelated task contains no Houmao outcome
- **WHEN** a request does not require Houmao knowledge, state, routing, or action
- **THEN** no Houmao system-skill root is selected implicitly

### Requirement: Actor entrypoints use broad actor-scoped implicit invocation
The packaged `houmao-admin-entrypoint` and `houmao-agent-entrypoint` skills SHALL declare narrow implicit activation in the system-skill manifest and SHALL expose synchronized host metadata that permits implicit invocation.

Within that activation posture, each entrypoint SHALL match any Houmao-related request in its actor context rather than only fully specified or executable operations. Missing targets or inputs SHALL remain post-trigger gates.

The admin entrypoint SHALL apply when the assistant acts for a human operator. The agent entrypoint SHALL apply only in a genuine Houmao-managed agent context. Both entrypoints SHALL remain directly invokable by their exact handles.

#### Scenario: Natural operator information request selects the admin entrypoint
- **WHEN** an operator agent with the admin pack receives a natural informational request about Houmao without a skill handle
- **THEN** `houmao-admin-entrypoint` is the expected initial root
- **AND THEN** it handles the request under human-operator posture

#### Scenario: Natural incomplete operator task selects the admin entrypoint
- **WHEN** an operator requests a recognizable Houmao operation but omits a required target
- **THEN** `houmao-admin-entrypoint` is eligible for implicit selection
- **AND THEN** the missing target is handled after activation rather than preventing activation

#### Scenario: Natural managed request selects the agent entrypoint
- **WHEN** a genuine managed agent with the agent pack receives a Houmao-related informational or operational request without a skill handle
- **THEN** `houmao-agent-entrypoint` is the expected initial root
- **AND THEN** its execution phase determines whether identity verification is required

#### Scenario: User invokes an entrypoint manually
- **WHEN** a caller submits `$houmao-admin-entrypoint ...` or `$houmao-agent-entrypoint ...` in the matching actor context
- **THEN** the named entrypoint follows the same intent, actor, identity, target, and routing contract used after implicit selection

### Requirement: Entrypoints classify intent before operational gates
After invocation, each actor entrypoint SHALL classify the request as informational, operational, unrelated, unsupported, or an explicitly selected downstream route before target discovery, sibling loading, or operational command execution.

Informational requests SHALL be answered locally and read-only. They SHALL NOT perform target discovery or load shared routines or a loop sibling. Agent informational requests SHALL NOT run managed-self identity verification.

For operational requests, the admin entrypoint SHALL establish its immutable admin frame before substantive routing. The agent entrypoint SHALL run exactly `houmao-mgr --print-json agents self identity`, validate fresh context-matching evidence, and fail closed before selecting or delegating a substantive route when verification fails.

After the actor gate, the entrypoint SHALL select exactly one eligible route, resolve required inputs and targets, delegate with the immutable handoff frame when needed, honor the supported admin join transition, and report the outcome.

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

### Requirement: Admin welcome is strictly manual
`houmao-admin-welcome` SHALL declare explicit activation in the system-skill manifest and SHALL expose synchronized host metadata with implicit invocation disabled.

Only an explicit `$houmao-admin-welcome ...` prompt SHALL select welcome. Natural first-contact, route-comparison, command-learning, reorientation, or guided-tour requests SHALL select the admin entrypoint, which SHALL return concise local read-only guidance and MAY recommend the exact manual welcome command but MUST NOT invoke welcome.

Empty admin-entrypoint invocation and retained welcome-style compatibility commands SHALL remain local read-only entrypoint requests and SHALL NOT delegate to welcome. Once explicitly invoked, welcome SHALL remain read-only and MAY hand an actionable request outward to the admin entrypoint under its existing safety contract.

#### Scenario: Natural first-contact request selects the admin entrypoint
- **WHEN** an operator agent receives a natural first-use question about Houmao without a skill handle
- **THEN** `houmao-admin-entrypoint` is the expected initial root
- **AND THEN** it may recommend `$houmao-admin-welcome` but neither selects nor delegates to welcome

#### Scenario: User manually starts the guided tour
- **WHEN** the user explicitly invokes `$houmao-admin-welcome start a guided tour`
- **THEN** welcome provides its read-only guided orientation
- **AND THEN** the admin entrypoint is not substituted as the initial root

#### Scenario: Empty admin entrypoint stays local
- **WHEN** the user explicitly invokes `$houmao-admin-entrypoint` without a task
- **THEN** the admin entrypoint returns concise read-only route guidance and may recommend the manual welcome command
- **AND THEN** it does not invoke welcome

#### Scenario: Explicit welcome receives an actionable task
- **WHEN** an explicitly invoked welcome request contains concrete operational context
- **THEN** welcome remains read-only and may hand the complete context to the admin entrypoint
- **AND THEN** welcome does not execute the operation itself

### Requirement: Shared and loop roots remain explicit initial roots
`houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` SHALL remain explicit-only for host-level initial selection and SHALL expose synchronized host metadata that disables implicit invocation.

An implicitly selected actor entrypoint MAY delegate ordinary work to shared routines and MAY delegate loop work when the user explicitly distinguishes pro or lite. Such downstream routing SHALL NOT change the delegated skill's explicit initial-root policy.

Generic loop wording SHALL NOT select pro or lite automatically.

#### Scenario: Natural ordinary task delegates through an entrypoint
- **WHEN** a natural Houmao request maps to an ordinary shared routine in an intended actor context
- **THEN** the actor entrypoint is selected as the initial root
- **AND THEN** it delegates to `houmao-shared-routines` with the immutable actor frame
- **AND THEN** shared routines is not treated as the directly implicit initial root

#### Scenario: Natural request explicitly distinguishes a loop sibling
- **WHEN** a natural Houmao request explicitly asks for the pro or lite loop without using a skill handle
- **THEN** the matching actor entrypoint is selected as the initial root
- **AND THEN** it MAY delegate to the explicitly distinguished top-level loop sibling
- **AND THEN** the loop sibling remains ineligible for direct host-level implicit selection

#### Scenario: Generic loop wording does not choose a loop
- **WHEN** a natural request describes a loop but does not distinguish pro from lite
- **THEN** neither loop root is selected automatically
- **AND THEN** an eligible actor entrypoint MAY ask for or explain the required choice without creating loop files

### Requirement: Deployment selects the actor pack independently of activation
Explicit operator installation without a pack override SHALL continue to select the admin pack. Managed launch and managed join SHALL continue to select the agent pack by default.

The admin pack SHALL contain admin welcome, admin entrypoint, shared routines, and both loop siblings. The agent pack SHALL contain agent entrypoint, shared routines, and both loop siblings, and SHALL NOT contain admin welcome or admin entrypoint.

Changing activation posture MUST NOT dynamically compose skill content, alter static copy or symlink projection, or inject the admin entrypoint into a managed-agent home.

#### Scenario: Operator manually installs the default surface
- **WHEN** a user runs the supported system-skill installer without an explicit pack override
- **THEN** the installer selects the admin pack
- **AND THEN** that selection occurs only because the user invoked installation

#### Scenario: Houmao constructs a managed home
- **WHEN** managed launch or join performs default system-skill installation
- **THEN** it installs the agent pack and not the admin pack
- **AND THEN** the managed agent receives `houmao-agent-entrypoint` as its only actor entrypoint

#### Scenario: Static skills are installed after the policy change
- **WHEN** either actor pack is copied, symlinked, or installed through a standard Skills CLI selection
- **THEN** every selected skill remains a complete checked-in static directory
- **AND THEN** no runtime-composed entrypoint or subskill tree is generated

### Requirement: Actor context disambiguates combined installations
When an advanced user explicitly installs both packs into one tool home, implicit selection SHALL still follow the current execution context rather than prompt claims alone.

Raw human-operator context SHALL select the admin entrypoint for Houmao-related requests. Genuine managed context SHALL select the agent entrypoint and SHALL require its identity gate for operational work. Prompt wording alone MUST NOT convert either actor context into the other.

#### Scenario: Combined home is used by a raw operator agent
- **WHEN** both packs are installed but the current session is a raw human-operator context
- **THEN** a Houmao-related request selects the admin entrypoint
- **AND THEN** the agent entrypoint is not selected from a prompt claim of managed identity

#### Scenario: Combined home is used by a managed agent
- **WHEN** both packs are installed but the current session is a genuine Houmao-managed context
- **THEN** a Houmao-related request selects the agent entrypoint
- **AND THEN** operational work performs fresh identity verification
- **AND THEN** the admin entrypoint is not selected merely because a human supplied the task

