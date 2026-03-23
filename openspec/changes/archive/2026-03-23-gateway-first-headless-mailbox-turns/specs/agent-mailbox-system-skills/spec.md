## ADDED Requirements

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade
When a live loopback gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL treat that shared gateway facade as the default routine action surface for ordinary mailbox work.

Projected mailbox system skills for both filesystem and Stalwart transports SHALL present that default structurally: a gateway-first routine-actions section first, followed by transport-local fallback guidance for no-gateway or transport-specific work.

For this change, ordinary mailbox work includes:

- checking unread mail,
- sending one new message,
- replying to one existing message, and
- marking one processed message read.

For attached filesystem sessions, the projected mailbox system skills SHALL present direct managed-script flows such as `deliver_message.py` or `update_mailbox_state.py` as fallback guidance for no-gateway sessions or transport-specific work outside the shared facade rather than as the first-choice path for ordinary attached-session turns.

For attached Stalwart sessions, the projected mailbox system skills SHALL present direct env-backed transport access as fallback guidance rather than as the first-choice path for ordinary attached-session turns.

#### Scenario: Attached filesystem session replies without reconstructing transport-local delivery
- **WHEN** an attached filesystem mailbox session needs to perform one routine reply in a bounded turn
- **THEN** the projected mailbox system skill directs the agent toward the shared gateway mailbox operations for `check`, `reply`, and read-state update
- **AND THEN** the agent does not need to reconstruct `deliver_message.py` payload fields or raw threading metadata to complete that routine action

#### Scenario: Filesystem session without gateway still has a direct fallback path
- **WHEN** a filesystem mailbox-enabled session has no live shared gateway mailbox facade
- **THEN** the projected mailbox system skill may fall back to direct managed-script guidance for the mailbox action
- **AND THEN** that fallback remains transport-specific rather than being restated inside the role or recipe
