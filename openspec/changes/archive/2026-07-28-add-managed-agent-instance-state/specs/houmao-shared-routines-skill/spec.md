## ADDED Requirements

### Requirement: Shared routines exposes actor-scoped instance state
The public shared-routines skill SHALL expose runtime-variable and mindset operations through the existing `houmao-agent-instance` child.

#### Scenario: Admin invokes state mutation
- **WHEN** actor posture is admin and one target is explicit
- **THEN** the child SHALL expose inspection and mutation commands

#### Scenario: Managed agent invokes state access
- **WHEN** the `as-agent` qualifier verifies a current managed runtime
- **THEN** the child SHALL expose self read and snapshot commands only
