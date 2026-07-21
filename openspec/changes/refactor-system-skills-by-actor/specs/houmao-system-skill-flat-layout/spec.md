## ADDED Requirements

### Requirement: Public discovery remains flat while protected implementation is nested
Houmao SHALL project public system skills as top-level directories in the established tool-native skill root.

Protected mounts and routines SHALL appear only below executable public entrypoints. The packaged source SHALL separate `public/` and `protected/` trees rather than placing every routine directly under the asset root.

#### Scenario: Operator inspects an installed admin pack
- **WHEN** an operator lists the top-level Houmao skills in a supported home
- **THEN** only `houmao-admin-welcome` and `houmao-admin-entrypoint` appear for the admin pack
- **AND THEN** the entrypoint contains nested protected implementation

### Requirement: Nested layout expresses ownership rather than workflow families
The nested path SHALL express the entrypoint, protected mount, and true subskill ownership chain.

Mailbox, project, loop, and utility labels SHALL NOT create independently installable filesystem families. Commands and references SHALL remain beneath the skill that owns them.

#### Scenario: Mailbox routine is installed for a managed agent
- **WHEN** the agent pack includes a mailbox routine
- **THEN** the routine appears under `houmao-agent-entrypoint/subskills/houmao-shared-routines/subskills/`
- **AND THEN** no top-level mailbox family or peer mailbox skill is projected

## REMOVED Requirements

### Requirement: Houmao-owned system skills use a flat packaged asset layout
**Reason**: Only public discovery remains flat; protected source and installed implementation are nested.
**Migration**: Move public skills under `public/` and protected routine sources under `protected/houmao-shared-routines/`.

### Requirement: Grouping is expressed through reserved names and named sets rather than filesystem families
**Reason**: Named sets are removed and ownership nesting now carries implementation structure.
**Migration**: Use pack metadata for installation grouping and nested skill ownership for implementation grouping.

