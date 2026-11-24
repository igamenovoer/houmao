# Spec Delta

## ADDED Requirements

### Requirement: Messaging guidance uses the gateway prompt receipt

The packaged messaging skill SHALL report admission and handoff from the first gateway prompt receipt. It SHALL use read-only evidence for further observation and preserve uncertainty when that evidence cannot establish the outcome.

#### Scenario: The target queues a prompt

- **WHEN** the receipt reports `outcome: queued` and `sent: false`
- **THEN** the skill reports accepted queueing with the available operation and native IDs
- **AND THEN** it retains that result without another submission for confirmation or output formatting

#### Scenario: The caller needs to observe a prior submission

- **WHEN** the caller needs more than the prompt receipt
- **THEN** the skill directs it to a saved headless turn or authorized service request lookup when the receipt identifies one
- **AND THEN** it explains the limits of Web and TUI state or history when no exact read result is available
