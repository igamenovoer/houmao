# Spec Delta

## MODIFIED Requirements

### Requirement: The scoped gateway CLI requests a browser terminal link

`houmao-mgr agents single --agent-id <id> gateway terminal-entry` SHALL request an unsigned read-only link from the selected agent's verified running owner-local gateway. `--agent-name` SHALL use existing selected-agent resolution. `--interact` SHALL use open admin authority or an enrolled administrator signer according to the verified roster. The command SHALL return `url`, `expires_at_utc`, and `mode` without following the URL, which help SHALL describe as a bearer secret.

#### Scenario: An operator requests a read-only link

- **WHEN** an operator requests a browser terminal link for a live tmux-backed agent without a signer
- **THEN** the CLI returns a link for viewing and its expiry in the selected output mode
- **AND THEN** the URL uses the existing gateway listener and grants only the view stream

#### Scenario: An operator explicitly requests interaction

- **WHEN** `--interact` is supplied for a keyed gateway and the selected signer has current enrolled administrator authority
- **THEN** the command returns a one-time link for the admin terminal mode
- **AND THEN** unsigned or nonadmin attempts on the keyed gateway produce a safe refusal without a fallback to another signer or mode

#### Scenario: An operator requests interaction on an open gateway

- **WHEN** `--interact` is supplied without an explicit signer and the verified owner-local gateway reports an empty roster
- **THEN** the command requests a one-time interactive link unsigned and returns it with its expiry
- **AND THEN** the gateway checks the current verified policy before granting access

#### Scenario: A gateway changes during unsigned entry

- **WHEN** the roster becomes keyed before open issuance or the selected gateway identity changes during an unsigned request
- **THEN** the CLI refuses to return the link and asks for a fresh request
- **AND THEN** the command neither retries under a different authority nor changes the selected access mode

#### Scenario: A running gateway or suitable transport is unavailable

- **WHEN** the selected gateway is detached, stale, or available only through an unsupported route
- **THEN** the command fails with actionable owner-local guidance
- **AND THEN** the command opens no terminal, starts no listener or gateway, and does not use another target
