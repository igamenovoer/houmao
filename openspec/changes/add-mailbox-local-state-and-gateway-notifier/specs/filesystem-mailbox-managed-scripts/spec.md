## ADDED Requirements

### Requirement: Managed mailbox helpers update shared catalog state and mailbox-local state consistently
Python managed mailbox helpers under `rules/scripts/` SHALL keep shared mailbox-root catalog state and mailbox-local mailbox-view state consistent during delivery, mailbox-state mutation, and repair.

Delivery helpers SHALL:

- update shared-root structural mailbox catalog data,
- initialize sender mailbox-local state deterministically,
- initialize recipient mailbox-local state deterministically.

Mailbox-state update helpers SHALL mutate the addressed mailbox's local mailbox-state database rather than requiring shared-root aggregate recipient-state tables to remain authoritative.

Repair helpers SHALL rebuild shared-root structural catalog state and mailbox-local mailbox-view state through their respective recovery paths without inventing aggregate recipient-status mirrors.

#### Scenario: Delivery initializes sender and recipient local mailbox state
- **WHEN** an operator or agent invokes `deliver_message.py` successfully for one sender and one or more recipients
- **THEN** the helper updates the shared mailbox-root structural catalog needed for canonical messages and projections
- **AND THEN** it initializes the sender and recipient mailbox-local state records with deterministic defaults in their respective mailbox-local SQLite databases

#### Scenario: Mailbox-state helper updates one addressed mailbox locally
- **WHEN** an operator or agent invokes `update_mailbox_state.py` to mark a message read for one mailbox address
- **THEN** the helper updates that mailbox address's local mailbox-state SQLite data
- **AND THEN** the helper does not depend on a shared aggregate recipient-state mirror to make that mutation authoritative

#### Scenario: Repair rebuilds local mailbox state when only structural mailbox data survives
- **WHEN** repair finds canonical message files and mailbox projections but one mailbox-local SQLite database is missing or unreadable
- **THEN** the repair flow can recreate deterministic local mailbox state for that mailbox from the available structural mailbox artifacts
- **AND THEN** the rebuilt mailbox-local state does not require inventing a shared aggregate read-state table
