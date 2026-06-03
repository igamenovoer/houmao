## ADDED Requirements

### Requirement: Project mailbox CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide entries for maintained project mailbox command surfaces used by system skills.

At minimum, the registry SHALL cover project mailbox initialization, status, repair, cleanup, account inspection, message listing, message inspection, and message clearing commands.

Each project mailbox template SHALL preserve project-root selection semantics by avoiding arbitrary mailbox-root flags unless the underlying project command supports them.

#### Scenario: Project mailbox message get renders project command
- **WHEN** an agent renders `project.mailbox.messages.get` with address and message id fields
- **THEN** the rendered argv maps to `houmao-mgr project mailbox messages get`
- **AND THEN** it does not add a shared mailbox-root override

#### Scenario: Project mailbox repair renders explicit cleanup posture only
- **WHEN** an agent renders a project mailbox repair template without an explicit cleanup or quarantine posture
- **THEN** the rendered argv omits those posture flags
- **AND THEN** the underlying project mailbox command keeps its own defaults
