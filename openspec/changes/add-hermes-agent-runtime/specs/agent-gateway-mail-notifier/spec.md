# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway notifier readiness honors style-classified Claude suggestions
For parser-backed TUI gateway targets, the mail notifier SHALL continue using the tracked prompt-readiness contract to decide whether notifier prompt enqueueing is safe.

When eligible inbox work exists, queue admission gates pass, and the tracked state reports ready posture because the only visible Claude prompt payload is a style-classified ghost suggestion, the notifier SHALL NOT defer solely because stripped prompt text is non-empty.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The notifier SHALL NOT add exact-text heuristics for Claude suggestions. Provider-specific suggestion recognition SHALL remain in the selected tracked-TUI profile.

When the tracked state reports real draft editing, the notifier SHALL continue to defer rather than overwriting operator-authored prompt input.

#### Scenario: Notifier enqueues while Claude shows only a styled suggestion
- **WHEN** a TUI-backed Claude gateway target has eligible inbox work
- **AND WHEN** queue admission gates pass
- **AND WHEN** the tracked state reports `turn.phase=ready`, `surface.editing_input=no`, and `surface.ready_posture=yes` for a prompt containing only a style-classified ghost suggestion
- **THEN** the notifier may enqueue the ordinary mail notification prompt
- **AND THEN** it does not record a busy skip solely because the stripped prompt line contains suggestion text

#### Scenario: Notifier still defers over a real draft
- **WHEN** a TUI-backed Claude gateway target has eligible inbox work
- **AND WHEN** the tracked state reports `surface.editing_input=yes` for real operator draft input
- **THEN** the notifier defers notifier prompt enqueueing
- **AND THEN** it preserves the operator's prompt input instead of overwriting it

#### Scenario: Suggestion text wording is not a notifier concern
- **WHEN** Claude Code changes the text of an auto-suggestion while the tracked profile still classifies it as ghost suggestion content from styling
- **THEN** notifier readiness behavior remains based on the tracked readiness fields
- **AND THEN** the notifier does not require a literal suggestion-text allowlist

#### Scenario: Hermes Notifier Uses Native Readiness

- **WHEN** Inbox work is eligible for a Hermes TUI agent
- **THEN** the notifier uses the owner's fresh native idle check before submission
- **AND THEN** known busy or unavailable state defers the reminder without a native submission

### Requirement: Reminder deduplication remains cycle-scoped
The notifier SHALL permit periodic reminders for unchanged eligible work under change 01's channel contract. It SHALL prevent overlapping attempts and duplicate admission of the same owner/channel/binding cycle. For a Hermes TUI, the notifier SHALL retain the exact native admission while its accepted reminder is queued, active, or unresolved. Sync checkpoints SHALL describe observed mailbox changes, not notification delivery or processing acknowledgements.

#### Scenario: Unchanged online mail repeats at later intervals
- **WHEN** online mail remains eligible across reminder intervals and the body is ready
- **THEN** separate due cycles can each admit a reminder
- **AND THEN** restored sync state does not permanently suppress that mail

#### Scenario: Same cycle is retried after reconnect
- **WHEN** two attempts represent one already-admitted reminder cycle
- **THEN** no second pending wakeup is admitted for that cycle

#### Scenario: A Human Turn Races a Hermes Reminder

- **WHEN** a Hermes TUI passes the final readiness check and commits the reminder to its native queue
- **THEN** the notifier records native acceptance for that reminder cycle and observes its settlement
- **AND THEN** later polls do not submit a duplicate or overlapping reminder while that admission is unresolved
- **AND THEN** native acceptance does not mark mail read, processed, or archived
- **AND THEN** unchanged eligible mail can trigger a later due reminder after settlement

### Requirement: Online notifier work is fenced to its binding
Notifier work SHALL carry channel, binding ID, and revision authority through observation, admission, and pending dispatch. Detach/replacement SHALL invalidate superseded observations and requests that have not reached native handoff. A verified Hermes queue receipt establishes native handoff even before the reminder starts. Prompts SHALL supply the expected binding ID so an already-running round cannot silently operate on a replacement account.

#### Scenario: Replacement occurs before queued reminder dispatch
- **WHEN** a pending reminder belongs to an account that is detached or replaced
- **THEN** it is cancelled or rejected before body dispatch
- **AND THEN** the new account is not contacted because of the old reminder

#### Scenario: Hermes Has Accepted a Reminder Before Replacement

- **WHEN** the binding changes after Hermes accepts the old binding's queued reminder
- **THEN** the notifier retains its original receipt and does not issue a second copy
- **AND THEN** the admitted text remains bound to the old binding so it cannot operate on the replacement account

### Requirement: Notifier Observes Backend Inbox Placement

The notifier SHALL use bounded observations of the backend's authoritative Inbox for eligible counts, compaction, and prompt content. Before native handoff it SHALL recheck current Inbox eligibility under the existing binding and readiness rules. Mail in backend Archive falls outside notifier work.

#### Scenario: Mail Archived at Delivery Is Outside the Notifier Inbox

- **WHEN** the bound backend files a blocked new message directly into Archive and the Inbox has no eligible items
- **THEN** the notifier records no eligible work and enqueues no reminder or compaction
- **AND THEN** the gateway leaves the archived message in its backend folder

#### Scenario: The Backend Moves Mail Before Queued Handoff

- **GIVEN** a reminder represents an Inbox message from a recent notifier observation
- **WHEN** the backend moves that message out of Inbox before dispatch
- **THEN** the gateway uses bounded backend evidence to omit that message from the reminder
- **AND THEN** it skips the reminder if no eligible work remains in it

#### Scenario: A Policy Revision Leaves Backend Inbox State Unchanged

- **WHEN** a backend policy revision leaves a message in Inbox with unchanged eligibility
- **THEN** the gateway observes the message under the selected notification mode and existing admission rules
- **AND THEN** the policy revision alone leaves any queued reminder and recorded compaction state intact

#### Scenario: Hermes Reminder Work Is Revalidated Before Native Submit

- **WHEN** a gateway-local pending reminder reaches dispatch for a Hermes TUI
- **THEN** the notifier revalidates Inbox eligibility and binding before the native submit
- **AND THEN** a later native queued status does not authorize a second handoff or change mailbox placement
