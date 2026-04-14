## ADDED Requirements

### Requirement: Runtime-owned mailbox workflow skills use archive as completion
Projected runtime-owned mailbox workflow skills SHALL instruct agents to treat archive, not read state, as the completion signal for processed mailbox work.

The `houmao-process-emails-via-gateway` workflow SHALL direct agents to list open inbox work through the gateway, choose relevant messages for the current round, peek or read selected messages intentionally, perform the requested work, reply or acknowledge when appropriate, archive only successfully processed messages, and stop after the round.

Deferred, skipped, or not-yet-completed messages SHALL remain unarchived so later notifier rounds can wake the agent again.

#### Scenario: Successfully processed mail is archived
- **WHEN** an agent finishes processing selected mailbox work during a notifier-driven round
- **THEN** the projected workflow skill instructs the agent to archive the successfully processed messages through the gateway or manager fallback surface
- **AND THEN** unfinished messages remain unarchived for later notification

### Requirement: Runtime-owned mailbox skills distinguish list, peek, read, mark, move, and archive
Projected runtime-owned mailbox skills SHALL present the ordinary mailbox action set as status, list, peek, read, send, post, reply, mark, move, archive, and resolve-live.

The skills SHALL explain that listing and peeking do not mark a message read, that reading marks a message read, that reply marks the parent answered, and that archive closes processed inbox work.

The skills SHALL keep manual marking available as a repair or operator-directed action rather than as the normal completion step for processed mail.

#### Scenario: Skill user can inspect without marking read
- **WHEN** an agent follows projected mailbox skill guidance to inspect a message for triage
- **THEN** the skill presents `peek` as the non-mutating body-inspection action
- **AND THEN** it reserves `read` for the action that marks the message read

#### Scenario: Manual marking is not the normal completion path
- **WHEN** an agent follows projected mailbox skill guidance after completing a mailbox task
- **THEN** the skill directs the agent to archive the processed message
- **AND THEN** it presents manual `mark` only for explicit state repair or operator-directed state changes

## REMOVED Requirements

### Requirement: Filesystem mailbox system skills instruct agents to mark processed mail read explicitly
**Reason**: Marking read is no longer the completion signal for processed mail; archive is the completion signal and read is only a body-consumption state.
**Migration**: No compatibility migration is required. Skill text and examples must be updated directly to archive-after-processing behavior.
