## MODIFIED Requirements

### Requirement: Gateway notifier wake-up semantics are unread-set based rather than per-message based
When gateway-owned notifier behavior is enabled for a mailbox-backed session, the gateway SHALL treat notification eligibility as a function of whether unread mail exists for that session and whether the session is currently eligible to receive a reminder prompt.

If a poll cycle finds multiple unread messages, the gateway SHALL support satisfying notifier behavior with a single internal reminder prompt that summarizes the unread set for that cycle, including message metadata such as titles or identifiers.

The gateway SHALL NOT require one internal reminder prompt per unread message in order to satisfy notifier behavior.

If the unread set remains unchanged after an earlier reminder was delivered or enqueued, and a later poll finds the session eligible to accept a new prompt again, the gateway SHALL continue treating that unchanged unread set as eligible for another reminder.

The gateway SHALL NOT suppress a later reminder solely because a prior reminder targeted the same unread snapshot.

#### Scenario: Multiple unread messages can be summarized in one reminder prompt
- **WHEN** one notifier poll cycle observes more than one unread message for the same mailbox-backed session
- **THEN** the gateway may enqueue one internal reminder prompt that summarizes the unread set observed in that cycle
- **AND THEN** the gateway does not need to enqueue one reminder per unread message

#### Scenario: Unchanged unread set remains eligible after the session becomes ready again
- **WHEN** the notifier previously delivered or enqueued a reminder for one unread set
- **AND WHEN** a later poll finds the same unread set still present and still unread
- **AND WHEN** the managed session is again eligible to accept a new prompt
- **THEN** the gateway continues treating that unread set as eligible for another reminder
- **AND THEN** it does not suppress that later reminder solely because the unread snapshot is unchanged

#### Scenario: Operator activity does not retire unread reminder eligibility
- **WHEN** unread mail remains present after a prior reminder
- **AND WHEN** operator-driven commands or other unrelated session activity interrupt, replace, or sidetrack the earlier reminder flow
- **AND WHEN** a later poll finds the managed session eligible to accept a new prompt again
- **THEN** the gateway still treats the remaining unread mail as eligible for notifier reminder delivery
- **AND THEN** reminder eligibility continues to depend on unread mail plus live prompt readiness rather than on prior reminder history
