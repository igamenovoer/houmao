## ADDED Requirements

### Requirement: `houmao-mgr mailbox` renders expected mailbox-root state failures as actionable CLI errors

When a maintained `houmao-mgr mailbox ...` command that expects an existing supported filesystem mailbox root encounters an expected mailbox-root state failure, the command SHALL fail as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to mailbox commands that inspect or mutate existing mailbox-root state, including:

- `accounts list`
- `accounts get`
- `messages list`
- `messages get`
- `unregister`
- `repair`
- `cleanup`
- `clear-messages`
- `export`

Expected mailbox-root state failures include unsupported mailbox roots, missing protocol-version state, missing shared mailbox indexes, unreadable shared mailbox indexes, and missing active registrations.

When an inspection command such as `houmao-mgr mailbox accounts list` fails because the resolved mailbox root is missing its shared mailbox index, the error text SHALL direct the operator to run `houmao-mgr mailbox init` first.

#### Scenario: Accounts list on an uninitialized mailbox root fails as CLI error text

- **WHEN** an operator runs `houmao-mgr mailbox accounts list --mailbox-root /tmp/shared-mail`
- **AND WHEN** `/tmp/shared-mail` lacks the shared mailbox index required for account inspection
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error tells the operator to run `houmao-mgr mailbox init` first
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Cleanup on an unsupported mailbox root fails as CLI error text

- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the resolved mailbox root is missing required bootstrap state or is otherwise unsupported
- **THEN** the command exits non-zero with explicit CLI error text for that mailbox root
- **AND THEN** the operator does not see a raw mailbox-domain exception traceback
