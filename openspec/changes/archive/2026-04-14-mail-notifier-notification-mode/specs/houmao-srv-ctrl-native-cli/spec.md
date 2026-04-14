## ADDED Requirements

### Requirement: Native gateway mail-notifier CLI configures notification mode
`houmao-mgr agents gateway mail-notifier enable` SHALL accept an optional notifier mode argument with values `any_inbox` and `unread_only`.

When the operator omits the notifier mode, the command SHALL send the gateway notifier enable request with effective mode `any_inbox`.

When the operator supplies `unread_only`, the command SHALL send the gateway notifier enable request with mode `unread_only`.

The command output for notifier status and enable results SHALL preserve the `mode` field returned by the gateway.

#### Scenario: CLI enable defaults to any-inbox mode
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60` without a mode option
- **THEN** the CLI sends a notifier enable request with mode `any_inbox`
- **AND THEN** the emitted result includes the gateway-reported `mode`

#### Scenario: CLI enable accepts unread-only mode
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60 --mode unread_only`
- **THEN** the CLI sends a notifier enable request with mode `unread_only`
- **AND THEN** it does not require the operator to address the raw `/v1/mail-notifier` route directly

#### Scenario: CLI rejects invalid notifier mode
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --interval-seconds 60 --mode read`
- **THEN** the CLI rejects the invocation as invalid input
- **AND THEN** it does not send a notifier enable request with an unknown mode value
