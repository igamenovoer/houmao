## ADDED Requirements

### Requirement: Shared mailbox CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide entries for maintained shared mailbox command surfaces used by system skills.

At minimum, the registry SHALL cover mailbox initialization, status, registration, cleanup, export, and message inspection/mutation commands that already exist under `houmao-mgr mailbox ...`.

Each shared mailbox template SHALL describe mailbox root selection, principal/address fields, mode flags, export scope, message selectors, and conflicts between mutually exclusive options.

#### Scenario: Shared mailbox register renders explicit mode
- **WHEN** an agent renders a shared mailbox register template with explicit principal, address, and mode fields
- **THEN** the rendered argv maps to the maintained `houmao-mgr mailbox register` command
- **AND THEN** omitted confirmation and override flags remain absent

#### Scenario: Mailbox export scope conflicts block rendering
- **WHEN** an agent renders a mailbox export template with conflicting export scopes
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
