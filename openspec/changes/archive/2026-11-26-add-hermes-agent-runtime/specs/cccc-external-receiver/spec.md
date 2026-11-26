# Spec Delta

## MODIFIED Requirements

### Requirement: Success Means Confirmed Ordinary Handoff

Before attempting body delivery, a receiver SHALL durably register with CCCC the exact ordered set of attempts it will dispatch together. CCCC SHALL settle that set together after confirmed ordinary handoff to the body that passed its final readiness check. Houmao-local queue admission, stream or pull receipt, and provider storage SHALL remain distinct from confirmed handoff and task completion.

#### Scenario: Ready Body Confirms Handoff

- **WHEN** a current receiver confirms ordinary handoff of a registered batch to a ready body
- **THEN** CCCC records accepted handoff for every exact attempt in that batch
- **AND THEN** the provider tracks any later reply or task completion separately

#### Scenario: Adapter Can Only Confirm Queued Work

- **WHEN** a body adapter reports queued work without qualified native handoff evidence by the confirmation deadline
- **THEN** the receiver reports failure or uncertainty according to whether the adapter can establish that no handoff occurred

#### Scenario: Readiness Changes Before Any Handoff

- **WHEN** a registered batch encounters a definitive ready-only refusal before the body can receive it
- **THEN** CCCC records the dispatch as having had no handoff and allows the same receiver to defer that exact batch until readiness returns
- **AND THEN** only a new fenced start can authorize the later dispatch

#### Scenario: Hermes Accepts an Exact Registered Batch Into Its Native Queue

- **WHEN** a current receiver dispatches a registered ordered batch to a Hermes TUI that passed its native idle check
- **AND WHEN** Houmao verifies a durable native queue receipt for that batch and its captured body
- **THEN** CCCC records accepted handoff for every attempt in that batch
- **AND THEN** a queued entry remains with the native authority and is ineligible for automatic redelivery
- **AND THEN** receipt acceptance does not claim turn start, a reply, or task completion

#### Scenario: Hermes Queue Acknowledgment Is Unresolved

- **WHEN** a Hermes submission may have reached the native queue but the receiver cannot verify that exact admission
- **THEN** the provider records uncertainty for that dispatch
- **AND THEN** it does not enqueue another attempt automatically
