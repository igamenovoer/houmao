## ADDED Requirements

### Requirement: Shared routines exposes actor-scoped private workspace operations
The public shared-routines skill SHALL expose private workspace operations through the existing `houmao-agent-instance` child.

#### Scenario: Admin invokes workspace management
- **WHEN** actor posture is admin and one target is explicit
- **THEN** the child SHALL expose inspection and maintained mutation commands

#### Scenario: Managed agent invokes workspace access
- **WHEN** `as-agent` verifies the current runtime
- **THEN** the child SHALL expose semantic path reads only

### Requirement: Custom private workspaces do not route to the team workspace manager
Routing SHALL keep instance-owned private workspace contracts separate from standard multi-agent workspace topology.

#### Scenario: Agent definition declares semantic directories
- **WHEN** the directories belong to one managed-agent instance
- **THEN** shared routines SHALL use `houmao-agent-instance`, not `houmao-utils-workspace-mgr`
