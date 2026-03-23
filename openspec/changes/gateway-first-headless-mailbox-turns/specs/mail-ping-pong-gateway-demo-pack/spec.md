## ADDED Requirements

### Requirement: Tracked ping-pong turns use gateway-first shared mailbox actions when gateways are attached
When the tracked mail ping-pong demo runs with attached loopback gateways for its participants, the demo SHALL keep routine mailbox work on the shared gateway mailbox facade rather than teaching the participants to reconstruct direct filesystem helper flows during ordinary turns.

The tracked kickoff contract SHALL communicate the business inputs for the first send action, including the responder target, thread key, round limit, subject convention, and reply policy, without requiring the initiator prompt to restate direct filesystem delivery mechanics as the normal path.

Later notifier-driven turns SHALL identify one actionable unread ping-pong message through shared mailbox references, including thread and queued-work context sufficient for a bounded reply turn, and SHALL expect the participant to complete the bounded mailbox action for that target, including the follow-up read-state update after successful processing.

The tracked initiator and responder role overlays SHALL remain focused on ping-pong policy such as round semantics, who replies next, and when to stop rather than on transport-local mailbox implementation details.

#### Scenario: Kickoff remains policy-thin for an attached gateway run
- **WHEN** a developer starts the demo and submits kickoff for a run whose initiator has a live loopback gateway mailbox facade
- **THEN** the kickoff prompt tells the initiator what first ping-pong message to send and which thread policy to follow
- **AND THEN** the prompt does not need to restate direct filesystem helper recipes as the normal attached-session path

#### Scenario: Responder wake-up completes one bounded shared-mailbox task
- **WHEN** the responder later wakes through gateway notifier after receiving the first ping-pong message
- **THEN** the responder turn is framed around one actionable unread target identified through shared mailbox references
- **AND THEN** the responder is expected to reply in the same thread, mark the processed message read after success, and end the turn without transport-local mailbox reconstruction
