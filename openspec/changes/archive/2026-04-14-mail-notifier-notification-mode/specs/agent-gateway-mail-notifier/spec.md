## ADDED Requirements

### Requirement: Gateway mail notifier supports notification modes
The gateway mail notifier SHALL support a durable notification mode with values `any_inbox` and `unread_only`.

When callers enable or reconfigure the notifier without specifying a mode, the gateway SHALL use `any_inbox`.

The notifier status payload SHALL report the effective mode for both enabled and disabled notifier states.

The notifier poll SHALL always select from the current principal's inbox and SHALL exclude archived or otherwise closed mail. The mode SHALL determine only the read-state filter:

- `any_inbox` SHALL poll with `read_state=any` so read or answered unarchived inbox mail remains notifier-eligible.
- `unread_only` SHALL poll with `read_state=unread` so only unread unarchived inbox mail is notifier-eligible.

The notifier SHALL preserve the existing gateway readiness, prompt-readiness, busy-skip, and internal request-queue admission gates in both modes.

#### Scenario: Omitted mode enables any-inbox notification
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `enabled=true` and `interval_seconds=60` but no `mode`
- **THEN** the gateway stores the notifier as enabled with mode `any_inbox`
- **AND THEN** subsequent `GET /v1/mail-notifier` responses report `mode=any_inbox`

#### Scenario: Any-inbox mode notifies for read answered inbox mail
- **WHEN** the notifier mode is `any_inbox`
- **AND WHEN** a notifier poll finds an inbox message with `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Unread-only mode ignores read inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an inbox message with `read=true` and `archived=false`
- **THEN** the notifier does not treat that message as notification-eligible solely because it remains in the inbox
- **AND THEN** it does not enqueue a prompt solely because of that read message

#### Scenario: Unread-only mode notifies for unread inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an inbox message with `read=false` and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Archived mail is not notifier-eligible in either mode
- **WHEN** the notifier mode is `any_inbox` or `unread_only`
- **AND WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as notification-eligible
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

### Requirement: Gateway notifier prompt is mode-aware and preserves archive completion
When the gateway mail notifier enqueues an internal prompt, the prompt SHALL describe the effective notification mode in mailbox workflow terms.

For mode `any_inbox`, the prompt SHALL announce that open inbox mail exists and direct the agent to list open inbox mail for the current round.

For mode `unread_only`, the prompt SHALL announce that unread inbox mail triggered the notification and direct the agent to start from unread inbox mail for the current round.

In both modes, the prompt SHALL direct the agent to archive successfully processed mail and SHALL NOT present reading or marking read as the completion action.

#### Scenario: Any-inbox prompt names open inbox work
- **WHEN** the notifier enqueues a prompt in mode `any_inbox`
- **THEN** the prompt tells the agent that open inbox mail exists
- **AND THEN** it tells the agent to archive successfully processed mail

#### Scenario: Unread-only prompt names unread inbox trigger
- **WHEN** the notifier enqueues a prompt in mode `unread_only`
- **THEN** the prompt tells the agent that unread inbox mail triggered the notification
- **AND THEN** it still tells the agent to archive successfully processed mail

#### Scenario: Prompt does not restore mark-read completion
- **WHEN** the notifier enqueues a prompt in either mode
- **THEN** the prompt does not tell the agent that reading or marking read completes the work
- **AND THEN** the prompt keeps archive as the completion action for successfully processed mail
