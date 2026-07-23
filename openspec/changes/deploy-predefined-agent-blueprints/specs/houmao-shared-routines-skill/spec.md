## ADDED Requirements

### Requirement: Shared routines exposes the admin-only blueprint deployment route

The explicit-only public `houmao-shared-routines` root SHALL expose `agent-definition deploy-blueprint` through its existing parent-scoped `houmao-agent-definition` child.

A direct invocation without an inherited actor frame SHALL use the maintained default human-operator posture and MAY execute the route after normal project and input gates. An explicit `as-agent` invocation SHALL perform fresh managed-self verification and SHALL then reject `deploy-blueprint` because the child is admin-only.

The shared-routines router and system-skill manifest SHALL advertise the subcommand only in the admin-eligible agent-definition route. They SHALL NOT duplicate its procedure in the shared-routines root.

#### Scenario: Advanced operator invokes the shared route directly

- **WHEN** a human explicitly invokes `$houmao-shared-routines agent-definition deploy-blueprint`
- **THEN** shared routines defaults the caller to admin posture and loads the parent-scoped agent-definition command
- **AND THEN** the child performs its own project, source, input, preview, and mutation gates

#### Scenario: As-agent qualifier cannot access blueprint deployment

- **WHEN** a caller invokes `$houmao-shared-routines as-agent agent-definition deploy-blueprint`
- **THEN** shared routines does not expose or execute that admin-only definition mutation
