# Spec Delta

## ADDED Requirements

### Requirement: The scoped gateway CLI requests a browser terminal link

`houmao-mgr agents single --agent-id <id> gateway terminal-entry` SHALL request an unsigned read-only link from the selected agent's verified running owner-local gateway. `--agent-name` SHALL use existing selected-agent resolution. `--interact` SHALL explicitly request enrolled-admin interaction. The command SHALL return `url`, `expires_at_utc`, and `mode` without following the URL, which help SHALL describe as a bearer secret.

#### Scenario: An operator requests a read-only link

- **WHEN** an operator requests a browser terminal link for a live tmux-backed agent without a signer
- **THEN** the CLI returns a link for viewing and its expiry in the selected output mode
- **AND THEN** the URL uses the existing gateway listener and grants only the view stream

#### Scenario: An operator explicitly requests interaction

- **WHEN** `--interact` is supplied and the selected signer has current enrolled administrator authority
- **THEN** the command returns a one-time link for the admin terminal mode
- **AND THEN** unsigned or nonadmin attempts produce a safe refusal without a fallback to another signer or mode

#### Scenario: A running gateway or suitable transport is unavailable

- **WHEN** the selected gateway is detached, stale, or available only through an unsupported route
- **THEN** the command fails with actionable owner-local guidance
- **AND THEN** the command opens no terminal, starts no listener or gateway, and does not use another target
