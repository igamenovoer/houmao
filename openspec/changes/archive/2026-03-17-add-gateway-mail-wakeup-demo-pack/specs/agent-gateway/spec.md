## ADDED Requirements

### Requirement: Gateway notifier wake-up semantics are unread-set based rather than per-message based
When gateway-owned notifier behavior is enabled for a mailbox-backed session, the gateway SHALL treat notification eligibility as a function of whether unread mail exists for that session and whether the session is eligible to receive a reminder prompt.

If a poll cycle finds multiple unread messages, the gateway MAY enqueue a single internal reminder prompt that summarizes the unread set for that cycle, including message metadata such as titles or identifiers.

The gateway SHALL NOT require one internal reminder prompt per unread message in order to satisfy notifier behavior.

If the unread set has not changed since the last successful reminder and the messages remain unread, the gateway MAY skip emitting a duplicate reminder until the unread set changes or the messages are marked read explicitly.

#### Scenario: Multiple unread messages can be summarized in one reminder prompt
- **WHEN** one notifier poll cycle observes more than one unread message for the same mailbox-backed session
- **THEN** the gateway may enqueue one internal reminder prompt that summarizes the unread set observed in that cycle
- **AND THEN** the gateway does not need to enqueue one reminder per unread message

#### Scenario: Unchanged unread set does not force duplicate reminders
- **WHEN** the notifier previously delivered or enqueued a reminder for one unread set
- **AND WHEN** a later poll finds the same unread set still present and still unread
- **THEN** the gateway may treat that later poll as a duplicate and skip enqueueing a second reminder for the unchanged unread set

### Requirement: Gateway notifier records structured per-poll decision auditing for later review
When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

Each record SHALL capture enough detail to explain what the notifier saw and why it enqueued or skipped work, including at minimum:

- poll time,
- unread-count observation,
- unread-set identity or equivalent deduplication summary,
- request-admission state,
- active-execution state,
- queue depth,
- the notifier decision outcome, and
- enqueue identifiers or skip detail when applicable.

The gateway MAY continue to keep `gateway.log` rate-limited and human-oriented, but that human log SHALL NOT be the only durable source of per-poll notifier decision history.

Detailed per-poll decision history SHALL remain available through that durable audit table even if `GET /v1/mail-notifier` remains a compact status snapshot without last-decision summary fields.

#### Scenario: Busy poll records an explicit skip decision
- **WHEN** a notifier poll cycle finds unread mail while gateway admission is not open, active execution is running, or queue depth is non-zero
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record identifies the decision as a busy or ineligible skip and includes the eligibility inputs that caused the skip

#### Scenario: Enqueue poll records the created reminder request
- **WHEN** a notifier poll cycle finds unread mail and the gateway enqueues an internal reminder prompt
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record includes the reminder decision outcome and the created internal request identifier

#### Scenario: Durable audit history remains the detailed inspection surface
- **WHEN** an operator or demo helper needs the latest detailed notifier decision data
- **THEN** it can inspect the durable SQLite notifier audit history under the gateway root
- **AND THEN** the gateway does not need to expose additional last-decision summary fields on `GET /v1/mail-notifier` in order to satisfy this requirement
