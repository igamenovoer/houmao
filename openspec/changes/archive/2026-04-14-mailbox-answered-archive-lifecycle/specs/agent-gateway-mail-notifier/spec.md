## ADDED Requirements

### Requirement: Gateway mail notifier polls open inbox work
The gateway mail notifier SHALL inspect open inbox work through the gateway-owned shared mailbox facade for the managed session rather than using unread-only `check` behavior.

For this change, open inbox work SHALL mean messages in the current principal's inbox that are not archived or otherwise closed. Messages MAY be read or answered and still remain open inbox work.

When open inbox work is present, the notifier SHALL preserve the existing readiness and queue-admission gates before enqueueing a reminder prompt.

The notifier SHALL record audit inputs in open-work terms, including open-work count and an open-work set identity or equivalent summary, rather than unread-count-only terms.

#### Scenario: Answered inbox mail remains notifier-eligible
- **WHEN** a notifier poll finds an inbox message that is `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the managed session is eligible for a notifier prompt
- **THEN** the notifier treats that message as open inbox work
- **AND THEN** it may enqueue a reminder prompt through the gateway's durable internal request path

#### Scenario: Archived mail is not notifier-eligible
- **WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as open inbox work
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

### Requirement: Gateway notifier wake-up prompts instruct archive-after-processing workflow
When the gateway mail notifier enqueues an internal reminder for open inbox work, the prompt SHALL announce that open shared-mailbox work exists for the current session.

The prompt SHALL direct the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill for the current round, list mailbox work through the shared gateway mailbox API, process selected relevant mail, archive only successfully processed mail, and stop after the round.

The prompt SHALL distinguish safe triage from mutating reads by listing the current gateway mailbox lifecycle endpoints for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

The prompt SHALL NOT tell the agent that `mark-read` is the completion action.

#### Scenario: Prompt names archive as completion
- **WHEN** the notifier enqueues a wake-up prompt for open inbox work
- **THEN** the prompt tells the agent to archive successfully processed mail
- **AND THEN** it does not tell the agent to mark messages read as the completion signal

#### Scenario: Prompt advertises peek and read separately
- **WHEN** the notifier prompt provides the current mailbox gateway operation contract
- **THEN** it lists separate routes or action names for peeking and reading mail
- **AND THEN** it communicates that peeking does not mark mail read

## REMOVED Requirements

### Requirement: Gateway mail notifier polls gateway-owned mailbox state and only schedules notifications when the agent is idle
**Reason**: The old notifier polling contract was unread-state based; lifecycle processing now requires reminders for read or answered mail that remains unarchived in the inbox.
**Migration**: No compatibility migration is required. Notifier code, prompts, tests, and docs must use open inbox work terminology and list/read/peek/archive mailbox operations.

### Requirement: Gateway notifier wake-up prompts summarize unread shared-mailbox work through a template-driven gateway-first contract
**Reason**: The old wake-up prompt contract centered unread work and post-success mark-read behavior. The new lifecycle workflow centers open inbox work and archive-after-processing behavior.
**Migration**: No compatibility migration is required. Prompt templates should be updated directly to the open inbox work and archive workflow.
