## MODIFIED Requirements

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors

`houmao-mgr agents` commands that target one managed agent SHALL accept explicit identity selectors instead of relying on one positional managed-agent reference.

At minimum, managed-agent-targeting commands in the `agents`, `agents gateway`, `agents mail`, and `agents turn` families SHALL accept:

- `--agent-id <id>`
- `--agent-name <name>`

For these commands, callers SHALL provide exactly one of those selectors unless the command defines a separate current-session targeting contract.

`--agent-id` SHALL target the authoritative globally unique managed-agent identity.

`--agent-name` SHALL target the friendly managed-agent name and SHALL only succeed when the relevant authority can prove that exactly one live managed agent currently uses that name.

When local registry-first discovery finds no live managed agent whose friendly name matches the supplied `--agent-name`, the command SHALL preserve that selector-miss context in any resulting failure instead of surfacing only a later transport-level fallback failure.

If the command cannot complete fallback lookup through the default pair authority after such a local miss, it SHALL report both the local friendly-name miss and the remote lookup unavailability, and SHALL direct the operator toward a corrective retry path such as `houmao-mgr agents list`, the correct friendly managed-agent name, or `--agent-id`.

If the supplied `--agent-name` exactly matches one unique live local tmux/session alias but not that agent's friendly managed-agent name, the command SHALL state that `--agent-name` expects the friendly managed-agent name and SHALL direct the operator to retry with the published `agent_name` or `--agent-id`.

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

#### Scenario: Friendly-name miss reports local miss before remote-unavailable fallback

- **WHEN** an operator runs `houmao-mgr agents state --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** the default pair authority is unavailable for fallback lookup
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that no local managed agent matched friendly name `agent-test`
- **AND THEN** the error also states that remote pair-authority lookup could not complete
- **AND THEN** the error does not present pair-authority unavailability as the only problem

#### Scenario: Friendly-name selector that matches a tmux/session alias gives a corrective hint

- **WHEN** an operator runs `houmao-mgr agents show --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** exactly one live local managed agent uses tmux/session alias `agent-test`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that `--agent-name` expects the friendly managed-agent name rather than the tmux/session alias
- **AND THEN** the error identifies the matching agent's published friendly name or authoritative `agent_id` as the retry target

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required
