## ADDED Requirements

### Requirement: Gateway coalesces adjacent queued control intents

The gateway SHALL coalesce adjacent accepted queued control-intent records before those records execute against the managed agent.

Control-intent records SHALL be limited to queued `interrupt` requests and queued `submit_prompt` requests whose entire trimmed prompt exactly matches a recognized context-control command. The initial recognized context-control commands SHALL include `/compact`, `/clear`, and `/new`.

The gateway SHALL treat ordinary prompts, internal `mail_notifier_prompt` records, unsupported stored request kinds, and different managed-agent instance epochs as coalescing boundaries. The gateway SHALL NOT coalesce `running`, `completed`, `failed`, or already `coalesced` records.

The gateway SHALL preserve ordinary prompt order and content exactly.

#### Scenario: Duplicate interrupts collapse to one interrupt

- **WHEN** the accepted queue contains an adjacent run of multiple `interrupt` requests for the same managed-agent instance epoch
- **THEN** the gateway executes at most one interrupt for that run
- **AND THEN** the redundant interrupt records are marked as coalesced instead of running independently

#### Scenario: Duplicate context command prompts collapse to one prompt

- **WHEN** the accepted queue contains adjacent `submit_prompt` records whose trimmed prompts are all `/compact`
- **THEN** the gateway executes at most one `/compact` prompt for that run
- **AND THEN** the redundant `/compact` records are marked as coalesced instead of running independently

#### Scenario: Later context commands supersede earlier pending context commands

- **WHEN** the accepted queue contains an adjacent run of context-control prompts `/compact`, `/clear`, and `/new` for the same managed-agent instance epoch
- **THEN** the gateway executes only the strongest final effective context action for that run
- **AND THEN** `/new` supersedes pending `/clear` and `/compact`, and `/clear` supersedes pending `/compact`

#### Scenario: Mixed interrupt and context commands preserve one interrupt intent

- **WHEN** the accepted queue contains an adjacent run with one or more `interrupt` records and one or more recognized context-control prompt records for the same managed-agent instance epoch
- **THEN** the gateway preserves one effective interrupt intent and one final effective context-control prompt
- **AND THEN** the effective interrupt executes before the effective context-control prompt

#### Scenario: Ordinary prompts break coalescing runs

- **WHEN** an ordinary `submit_prompt` record appears between two control-intent records in the accepted queue
- **THEN** the gateway treats the ordinary prompt as a hard coalescing boundary
- **AND THEN** the gateway preserves the ordinary prompt order and does not merge control intents across it

#### Scenario: Internal notifier prompts are not coalesced

- **WHEN** an accepted internal `mail_notifier_prompt` record appears in the queue
- **THEN** the gateway does not classify that record as a coalescible control intent
- **AND THEN** the gateway does not merge ordinary or control work across that notifier record

#### Scenario: Epoch boundaries prevent coalescing

- **WHEN** adjacent accepted control-intent records have different `managed_agent_instance_epoch` values
- **THEN** the gateway does not coalesce those records together
- **AND THEN** existing replay and reconciliation safeguards remain authoritative for old-epoch work

#### Scenario: Coalescing leaves durable audit evidence

- **WHEN** the gateway removes an accepted request from execution by coalescing it into effective control work
- **THEN** the gateway marks that request with terminal state `coalesced`
- **AND THEN** the gateway records enough result metadata and gateway event data to identify the effective request or action that superseded it

#### Scenario: Coalesced records do not count as active queue depth

- **WHEN** a request has terminal state `coalesced`
- **THEN** gateway queue-depth reporting excludes that request
- **AND THEN** only accepted and running work contributes to active queue depth
