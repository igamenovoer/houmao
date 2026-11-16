# Spec Delta

## ADDED Requirements

### Requirement: Mailbox routines triage bounded metadata pages
Ordinary and notifier-driven routines SHALL start from one bounded metadata page for the selected channel/binding. They SHALL retrieve more pages only within an explicit round budget and fetch content only for selected messages through peek/read. They SHALL archive only successfully processed mail after required replies and stop after the round.

#### Scenario: Inbox is larger than one processing round
- **WHEN** the first metadata page has continuation but the round budget is reached
- **THEN** the routine leaves deferred work unarchived for later periodic reminders
- **AND THEN** it does not fetch all retained bodies before selecting work

#### Scenario: Metadata is insufficient for a selected task
- **WHEN** an agent selects a message as relevant
- **THEN** it explicitly peeks or reads the needed content and checks any completeness limitation
- **AND THEN** it does not assume a preview is the full task request

### Requirement: Online binding changes end stale processing rounds explicitly
A round SHALL retain its expected binding ID and channel. If attachment controls replace or detach that binding, the routine SHALL treat the conflict as an interrupted round rather than rediscover another account and continue its old actions. Credential refresh for the same binding SHALL not itself require a new agent identity or body conversation.

#### Scenario: Account changes before a fresh reply or send
- **WHEN** the expected online binding no longer matches during a round
- **THEN** the routine reports the conflict and does not send through the replacement account
- **AND THEN** uncompleted mail remains governed by its original mailbox state

### Requirement: Runtime mailbox guidance keeps credential administration outside ordinary mail work
Ordinary agent mailbox guidance SHALL use current scoped APIs or manager helpers and SHALL not instruct the agent to print, copy into project files, or discover unrelated credentials. Authorized operator guidance SHALL document explicit online attachment, private credential refresh, reconnect, and detach separately from routine mail processing.

#### Scenario: Online authentication expires during a round
- **WHEN** the online provider rejects the configured credential
- **THEN** the routine reports the binding's sanitized authentication failure
- **AND THEN** it does not scan ambient authentication files or switch to offline mail
