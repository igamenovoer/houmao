# Spec Delta

## ADDED Requirements

### Requirement: Online notifier observes bounded metadata work
Online notifier cycles SHALL use bounded metadata/change queries and derived eligible views. They SHALL not fetch full bodies or scan all retained inbox/archive history to decide whether a reminder is due. Readiness refusal SHALL not discard synchronized work. Audit summaries SHALL identify bounded samples or lower bounds rather than claim an incomplete sample is the complete inbox.

#### Scenario: Large retained history does not trigger body scans
- **WHEN** the online notifier polls an account with a large archive and eligible inbox work
- **THEN** its requests and metadata transfer respect the configured cycle budget
- **AND THEN** no message body values are requested merely for notification

#### Scenario: Body is busy after metadata synchronization
- **WHEN** a cycle observes eligible mail but body admission refuses a reminder
- **THEN** it records the readiness outcome without marking the mail processed
- **AND THEN** later intervals can remind for the same unchanged work

### Requirement: Reminder deduplication remains cycle-scoped
The notifier SHALL permit periodic reminders for unchanged eligible work under change 01's channel contract. It SHALL prevent overlapping attempts and duplicate admission of the same owner/channel/binding cycle. Sync checkpoints SHALL describe observed mailbox changes, not notification delivery or processing acknowledgements.

#### Scenario: Unchanged online mail repeats at later intervals
- **WHEN** online mail remains eligible across reminder intervals and the body is ready
- **THEN** separate due cycles can each admit a reminder
- **AND THEN** restored sync state does not permanently suppress that mail

#### Scenario: Same cycle is retried after reconnect
- **WHEN** two attempts represent one already-admitted reminder cycle
- **THEN** no second pending wakeup is admitted for that cycle

### Requirement: Online notifier work is fenced to its binding
Notifier work SHALL carry channel, binding ID, and revision authority through observation, admission, and pending dispatch. Detach/replacement SHALL invalidate superseded observations and unstarted requests. Prompts SHALL supply the expected binding ID so an already-running round cannot silently operate on a replacement account.

#### Scenario: Replacement occurs before queued reminder dispatch
- **WHEN** a pending reminder belongs to an account that is detached or replaced
- **THEN** it is cancelled or rejected before body dispatch
- **AND THEN** the new account is not contacted because of the old reminder

### Requirement: Sync recovery preserves compaction eligibility truth
Metadata cache eviction, checkpoint rebase, and credential refresh SHALL not by themselves reset one-shot compaction state for continuously eligible mail. Clearing that state SHALL require confirmed loss of eligibility or a different binding. Recovery SHALL revalidate known compaction entries in bounded batches when eligibility is uncertain.

#### Scenario: Cached entry is evicted and rediscovered
- **WHEN** a continuously eligible message leaves the metadata window and later reappears
- **THEN** its prior successful compaction remains remembered
- **AND THEN** periodic reminders can continue without another compaction for that eligibility stretch
