## ADDED Requirements

### Requirement: System-skills CLI reference documents static pack membership
The CLI reference SHALL list all standalone members of the admin and agent packs, identify shared ownership of `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`, and distinguish the sixteen shared children from installable roots.

It SHALL NOT describe protected mounts, audience-specific composed route files, or materialized entrypoint trees as current behavior.

#### Scenario: Reader checks the agent pack
- **WHEN** a reader opens the system-skills pack table
- **THEN** the agent pack contains agent entrypoint, shared routines, pro loop, and lite loop
- **AND THEN** all four appear as top-level static destinations

### Requirement: System-skills CLI reference documents shared-owner lifecycle behavior
The CLI reference SHALL explain install, status, upgrade, and uninstall behavior for overlapping pack members. It SHALL state that uninstall removes a shared projection only after its last owning pack is removed.

The reference SHALL describe v3 composed receipts as drifted and SHALL document transactional upgrade to v4 static roots, including conflict preservation and receipt-last commit.

#### Scenario: Reader plans to remove one of two installed packs
- **WHEN** both packs own shared members
- **THEN** the reference explains which exclusive entrypoint is removed
- **AND THEN** it explains why shared routines and loops remain for the other pack

### Requirement: CLI reference documents standard external skill installation
The system-skills reference SHALL link to the public static source collection and show that users may install it with normal Skills CLI or copy-paste workflows.

It SHALL explain that external standard installation has no Houmao pack receipt and requires explicit sibling selection, while `houmao-mgr system-skills` provides dependency-aware pack lifecycle management.

#### Scenario: Reader compares manager and Skills CLI
- **WHEN** a reader chooses an installation method
- **THEN** the reference distinguishes receipt ownership and automatic pack closure from independent skill selection
- **AND THEN** it provides the complete sibling list needed by the chosen actor entrypoint

### Requirement: CLI reference documents direct public invocation surfaces
The reference SHALL document normal admin and agent entrypoint forms, direct shared-routines advanced invocation, direct pro and lite invocation, and the optional managed-self qualifier for direct shared or loop calls.

It SHALL describe shared children with parent-qualified object notation and SHALL not advertise their old top-level `$houmao-<routine>` forms as current standalone triggers.

#### Scenario: Reader invokes a loop manually
- **WHEN** a reader chooses the pro loop skill
- **THEN** the reference shows `$houmao-agent-loop-pro <operation>`
- **AND THEN** it preserves the explicit manual activation boundary and `<loop-dir>` input rules
