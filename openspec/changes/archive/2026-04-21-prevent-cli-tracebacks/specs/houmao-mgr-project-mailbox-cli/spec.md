## ADDED Requirements

### Requirement: `houmao-mgr project mailbox` renders selected-overlay mailbox failures as actionable CLI errors

When a maintained `houmao-mgr project mailbox ...` command encounters an expected selected-overlay mailbox-root failure, the command SHALL exit non-zero with explicit CLI error text and SHALL NOT leak a Python traceback.

This SHALL apply at minimum to project mailbox commands that inspect or mutate existing selected-overlay mailbox state, including:

- `accounts list`
- `accounts get`
- `messages list`
- `messages get`
- `cleanup`
- `clear-messages`
- `export`

When the selected overlay mailbox root is missing its shared mailbox index or other required bootstrap state, the error text SHALL preserve selected-overlay mailbox wording and SHALL recommend `houmao-mgr project mailbox init` rather than the generic `houmao-mgr mailbox init` recovery path.

#### Scenario: Project mailbox accounts list on an uninitialized selected overlay fails without traceback

- **WHEN** an operator runs `houmao-mgr project mailbox accounts list`
- **AND WHEN** the selected overlay mailbox root exists but is missing the shared mailbox index required for account inspection
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error recommends `houmao-mgr project mailbox init`
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Project mailbox cleanup preserves selected-overlay failure wording

- **WHEN** an operator runs `houmao-mgr project mailbox cleanup`
- **AND WHEN** the selected overlay mailbox root is missing required bootstrap state or is otherwise unsupported for cleanup
- **THEN** the command exits non-zero with explicit CLI error text tied to the selected overlay mailbox root
- **AND THEN** the operator does not see raw generic mailbox-domain exception output or a Python traceback
