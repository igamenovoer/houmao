## ADDED Requirements

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors

`houmao-mgr agents` commands that target one managed agent SHALL accept explicit identity selectors instead of relying on one positional managed-agent reference.

At minimum, managed-agent-targeting commands in the `agents`, `agents gateway`, `agents mail`, and `agents turn` families SHALL accept:

- `--agent-id <id>`
- `--agent-name <name>`

For these commands, callers SHALL provide exactly one of those selectors unless the command defines a separate current-session targeting contract.

`--agent-id` SHALL target the authoritative globally unique managed-agent identity.

`--agent-name` SHALL target the friendly managed-agent name and SHALL only succeed when the relevant authority can prove that exactly one live managed agent currently uses that name.

#### Scenario: Exact selector by agent id is accepted

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` targets the managed agent whose authoritative identity is `abc123`
- **AND THEN** the operator does not need to rely on friendly-name uniqueness for that control action

#### Scenario: Friendly-name selector succeeds only when unique

- **WHEN** an operator runs `houmao-mgr agents show --agent-name gpu`
- **AND WHEN** exactly one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` targets that managed agent
- **AND THEN** the command succeeds without requiring the operator to spell the authoritative `agent_id`

#### Scenario: Friendly-name selector fails on ambiguity

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name gpu --prompt "..."`
- **AND WHEN** more than one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error directs the operator to retry with `--agent-id`

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required
