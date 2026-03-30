## MODIFIED Requirements

### Requirement: `houmao-mgr agents mailbox register` creates shared registration and persists session mailbox binding
`houmao-mgr agents mailbox register` SHALL register filesystem mailbox support for an existing local managed agent after launch or join.

At minimum, the command SHALL:

1. resolve the local managed-agent controller,
2. resolve the filesystem mailbox root from explicit override, environment override, or default,
3. derive default mailbox principal and full address from the managed-agent identity when the operator does not supply explicit values,
4. ensure the target address has an active shared mailbox registration using safe registration semantics by default and requiring explicit operator confirmation before any destructive replacement,
5. attach the resolved mailbox binding to the managed session,
6. persist that mailbox binding into the session manifest and registry-visible mailbox summary, and
7. accept `--yes` so an operator can confirm overwrite without an interactive prompt.

When the requested registration path would replace existing durable mailbox state, the CLI SHALL require explicit operator confirmation before applying the destructive replacement.
This confirmation requirement SHALL apply whether destructive replacement was requested explicitly through registration mode selection or reached from the default safe flow after conflict detection.
When `--yes` is absent and an interactive terminal is available, the CLI SHALL prompt before destructive replacement.
When `--yes` is absent and no interactive terminal is available, the CLI SHALL fail clearly before replacing shared mailbox state or mutating the managed session's mailbox binding.
If the operator declines the overwrite prompt, the command SHALL abort without replacing shared mailbox state and without mutating the managed session's mailbox binding.

After successful registration, later `houmao-mgr agents mail ...` commands SHALL treat the session as mailbox-enabled when the returned activation state is `active`.

#### Scenario: Headless local managed agent becomes mailbox-enabled immediately
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a local headless managed session
- **AND WHEN** no destructive replacement is required
- **THEN** the command safely registers `alice`'s mailbox address under `/tmp/shared-mail`
- **AND THEN** the session manifest persists the resulting mailbox binding
- **AND THEN** the command reports activation state `active`
- **AND THEN** later `houmao-mgr agents mail status --agent-name alice` succeeds without any launch-time mailbox flag

#### Scenario: Operator confirms overwrite for late mailbox registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator confirms overwrite
- **THEN** the command applies the overwrite-confirmed registration path
- **AND THEN** it persists the resulting mailbox binding into the session manifest and registry-visible mailbox summary

#### Scenario: Non-interactive late registration conflict without yes fails clearly
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** no interactive terminal is available
- **AND WHEN** `--yes` is not present
- **THEN** the command fails clearly before replacing shared mailbox state
- **AND THEN** it does not mutate the managed session's mailbox binding

#### Scenario: Yes skips overwrite prompt for late mailbox registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail --yes`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **THEN** the command applies the overwrite-confirmed registration path without prompting
- **AND THEN** it persists the resulting mailbox binding into the session manifest and registry-visible mailbox summary
