## MODIFIED Requirements

### Requirement: Native gateway mail-notifier CLI configures notification mode
`houmao-mgr agents gateway mail-notifier enable` SHALL accept an optional notifier mode argument with values `any_inbox` and `unread_only`.

When the operator omits the notifier mode, the command SHALL send the gateway notifier enable request with effective mode `any_inbox`.

When the operator supplies `unread_only`, the command SHALL send the gateway notifier enable request with mode `unread_only`.

`houmao-mgr agents gateway mail-notifier enable` SHALL also accept an optional `--appendix-text` argument that updates notifier `appendix_text`.

When the operator omits `--appendix-text`, the CLI SHALL send the notifier enable request without an appendix field so the gateway can preserve the stored appendix unchanged.

When the operator supplies non-empty `--appendix-text`, the CLI SHALL send that exact string as notifier `appendix_text`.

When the operator supplies `--appendix-text ""`, the CLI SHALL send `appendix_text=""` so the gateway clears the stored appendix.

The command output for notifier status and enable results SHALL preserve both the `mode` field and the effective `appendix_text` returned by the gateway.

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

#### Scenario: CLI omits appendix field when not provided
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60` without `--appendix-text`
- **THEN** the CLI sends the notifier enable request without an appendix field
- **AND THEN** the gateway can preserve previously stored appendix text unchanged

#### Scenario: CLI forwards non-empty appendix text
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60 --appendix-text "Watch for high-priority mailbox work first."`
- **THEN** the CLI sends that exact string as notifier `appendix_text`
- **AND THEN** the emitted result includes the gateway-reported effective appendix text

#### Scenario: CLI forwards empty appendix text to clear appendix
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60 --appendix-text ""`
- **THEN** the CLI sends `appendix_text=""` to the gateway
- **AND THEN** it does not reinterpret the empty string as omitted input
