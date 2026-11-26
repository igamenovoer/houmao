# Gateway Mail Notifier Delta

## MODIFIED Requirements

### Requirement: Gateway mail notifier polls open inbox work

The gateway mail notifier SHALL inspect open work in the bound mailbox backend's authoritative Inbox through the gateway-owned shared mailbox facade. The backend SHALL determine mailbox placement. The notifier SHALL exclude archived and closed mail. Read and answered Inbox messages remain eligible in `any_inbox` mode. The notifier SHALL preserve readiness and queue-admission checks and audit the eligible open-work count and set identity or equivalent summary.

#### Scenario: Acceptance criteria

- **GIVEN** a notifier polling the selected mailbox for open inbox work
- **THEN** it applies the notification mode to the backend's authoritative Inbox before identifying any work
- **AND THEN** it preserves readiness and queue-admission gates and audits the eligible set or its bounded summary

#### Scenario: Answered inbox mail remains notifier-eligible

- **WHEN** a notifier poll in `any_inbox` mode finds an Inbox message that is `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the managed session is eligible for a notifier prompt
- **THEN** the notifier treats that message as open inbox work
- **AND THEN** it can enqueue a reminder prompt through the gateway's durable internal request path

#### Scenario: Archived mail is not notifier-eligible

- **WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as open inbox work
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

#### Scenario: An Unblock Affects Future Inbox Delivery

- **GIVEN** the backend archived a message at delivery under the current block rule
- **WHEN** the owner removes the rule and the backend delivers a new message from the same sender to Inbox
- **THEN** the notifier evaluates the new Inbox message under the selected mode and current admission
- **AND THEN** the earlier message remains in Archive and outside reminder work

### Requirement: Gateway notifier wake-up prompts instruct archive-after-processing workflow

When the gateway mail notifier enqueues an internal reminder for open Inbox work, the prompt SHALL announce that the current session has Inbox mail. It SHALL direct the agent to use the installed `houmao-process-emails-via-gateway` skill, list Inbox work through the gateway mailbox API, process relevant mail, follow the binding's authorized completion path for successfully processed messages, and stop after the round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The prompt SHALL distinguish safe triage from mutating reads. It SHALL summarize the applicable gateway routes for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` according to the selected binding's capabilities and the session's authority.

The prompt SHALL reserve runtime archive for bindings that authorize it. On a protected binding, it SHALL direct the agent to report successfully processed mail for independently authorized owner archive through the backend. It SHALL omit runtime placement operations from the available routes and keep reading and marking read separate from completion.

#### Scenario: Prompt names archive as completion

- **WHEN** the notifier enqueues a wake-up prompt for open Inbox work
- **THEN** the prompt identifies archive of successfully processed mail as completion through the binding's authorized path
- **AND THEN** it keeps mark-read as a read-state change

#### Scenario: Prompt advertises peek and read separately

- **WHEN** the notifier prompt provides the current mailbox gateway operation contract and the binding supports both peek and read
- **THEN** it lists separate routes or action names for peeking and reading mail
- **AND THEN** it communicates that peeking leaves read state unchanged

#### Scenario: Protected Binding Directs Processed Mail to Owner Archive

- **WHEN** the notifier renders a prompt for a protected mailbox binding
- **THEN** it directs the agent to report successfully processed mail for independently authorized owner archive
- **AND THEN** the advertised runtime routes exclude ordinary archive, move, and archived-state updates

### Requirement: Gateway mail notifier supports notification modes
Each configured channel's gateway mail notifier SHALL support its own durable notification mode with values `any_inbox` and `unread_only`.

When callers enable or reconfigure the notifier without specifying a mode, the gateway SHALL use `any_inbox`.

The notifier status payload SHALL report the effective mode for both enabled and disabled notifier states.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The notifier poll SHALL select from the backend's authoritative Inbox for the current principal and exclude archived and closed mail. The mode SHALL determine the read-state selection:

- `any_inbox` SHALL poll with `read_state=any` so read or answered unarchived Inbox mail remains notifier-eligible.
- `unread_only` SHALL poll with `read_state=unread` so only unread unarchived Inbox mail is notifier-eligible.

The notifier SHALL preserve the existing gateway readiness, prompt-readiness, busy-skip, and internal request-queue admission gates in both modes.

#### Scenario: Omitted mode enables any-inbox notification
- **WHEN** a caller sends `PUT /v1/mail-notifier/{channel}` with `enabled=true` and `interval_seconds=60` but no `mode`
- **THEN** the gateway stores the notifier as enabled with mode `any_inbox`
- **AND THEN** subsequent `GET /v1/mail-notifier/{channel}` responses report `mode=any_inbox`

#### Scenario: Any-inbox mode notifies for read answered inbox mail
- **WHEN** the notifier mode is `any_inbox`
- **AND WHEN** a notifier poll finds an Inbox message with `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Unread-only mode ignores read inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an Inbox message with `read=true` and `archived=false`
- **THEN** the notifier does not treat that message as notification-eligible solely because it remains in the inbox
- **AND THEN** it does not enqueue a prompt solely because of that read message

#### Scenario: Unread-only mode notifies for unread inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an Inbox message with `read=false` and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Archived mail is not notifier-eligible in either mode
- **WHEN** the notifier mode is `any_inbox` or `unread_only`
- **AND WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as notification-eligible
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

### Requirement: Gateway notifier prompt is mode-aware and preserves archive completion

When the gateway mail notifier enqueues an internal prompt, the prompt SHALL describe the effective notification mode in mailbox workflow terms. In `any_inbox` mode it SHALL announce open Inbox work and direct the agent to list open Inbox mail. In `unread_only` mode it SHALL announce that unread Inbox mail triggered the notification and direct the agent to start from unread Inbox mail.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

In either mode, the prompt SHALL keep archive as the completion action for successfully processed mail. It SHALL direct the agent to runtime archive only when the binding and session authorize it. On protected bindings it SHALL direct the agent to independently authorized owner archive. Reading and marking read SHALL remain read-state changes.

#### Scenario: Any-inbox prompt names open inbox work

- **WHEN** the notifier enqueues a prompt in mode `any_inbox`
- **THEN** the prompt tells the agent that open Inbox mail exists
- **AND THEN** it directs the agent to the applicable archive completion path for successfully processed mail

#### Scenario: Unread-only prompt names unread inbox trigger

- **WHEN** the notifier enqueues a prompt in mode `unread_only`
- **THEN** the prompt tells the agent that unread Inbox mail triggered the notification
- **AND THEN** it directs the agent to the applicable archive completion path for successfully processed mail

#### Scenario: Prompt does not restore mark-read completion

- **WHEN** the notifier enqueues a prompt in either mode
- **THEN** the prompt describes reading and marking read as read-state changes
- **AND THEN** the prompt keeps archive as the completion action for successfully processed mail

#### Scenario: Processed Inbox Mail Awaits Owner Archive

- **GIVEN** a protected binding has successfully processed mail that remains in Inbox awaiting owner archive
- **WHEN** later notifier cycles observe that same mail
- **THEN** `any_inbox` can continue to remind while that mail remains eligible and admission permits it
- **AND THEN** `unread_only` still requires unread Inbox mail to trigger a reminder

### Requirement: Pre-notification compaction runs at most once per continuously eligible mail item
When `pre_notification_context_action=compact` is configured, the gateway mail notifier SHALL treat compaction as a one-shot preflight for each mail item's current eligibility stretch rather than as an action that repeats on every later notifier cycle.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For this requirement, a mail item's eligibility stretch lasts only while that message satisfies the authoritative backend Inbox state for the notifier's current mode:

- in `any_inbox`, while the message remains an unarchived inbox item,
- in `unread_only`, while the message remains unread and unarchived in the inbox.

The notifier SHALL remember which currently eligible `message_ref` values have already triggered successful pre-notification compaction during their current eligibility stretch.

When a later notifier cycle sees only previously remembered eligible mail, the notifier MAY still enqueue or deliver the semantic mailbox wake-up prompt according to the existing readiness and queue-admission rules, but it SHALL NOT run another pre-notification compaction solely because that same eligible mail remains present.

When a later notifier cycle sees at least one newly eligible mail item that has not yet triggered compaction during its current eligibility stretch, the notifier SHALL run at most one additional compaction preflight for that cycle before continuing with ordinary notifier prompt behavior.

When backend observations confirm that a previously remembered mail item has stopped satisfying the mailbox state for the selected mode, the notifier SHALL forget that item's compaction state. A future re-entry into eligibility begins a new eligibility stretch.

This compaction bookkeeping SHALL remain separate from mailbox read state, prompt-dedup decisions, and `last_notified_digest`-style notification timing metadata.

#### Scenario: Unchanged any-inbox mail does not re-trigger compaction
- **GIVEN** the notifier mode is `any_inbox`
- **AND GIVEN** message `A` remains the same unarchived eligible inbox mail across multiple notifier cycles
- **AND GIVEN** `A` already triggered one successful pre-notification compaction during its current eligibility stretch
- **WHEN** a later notifier cycle runs while `A` is still eligible
- **THEN** the notifier does not run another pre-notification compaction solely because `A` is still present
- **AND THEN** any repeated wake-up prompt behavior follows the existing readiness and queue-admission rules without a second compaction for `A`

#### Scenario: Newly eligible mail causes one new compaction for the expanded set
- **GIVEN** the notifier has already recorded successful compaction for currently eligible message `A`
- **AND GIVEN** a later notifier cycle sees eligible messages `A` and `B`, where `B` has newly entered the eligible set
- **WHEN** the notifier prepares the next wake-up cycle
- **THEN** the notifier runs at most one additional pre-notification compaction for that cycle
- **AND THEN** it records that both `A` and `B` have now triggered compaction during their current eligibility stretch

#### Scenario: Unread-only eligibility reset allows a future fresh compaction
- **GIVEN** the notifier mode is `unread_only`
- **AND GIVEN** message `A` previously triggered one successful pre-notification compaction while unread and unarchived
- **AND GIVEN** `A` later becomes ineligible because it is no longer unread or no longer in Inbox
- **WHEN** `A` later becomes eligible again in a new eligibility stretch
- **THEN** the notifier may run one fresh pre-notification compaction for `A`
- **AND THEN** it does not treat the earlier eligibility stretch as permanent suppression

## ADDED Requirements

### Requirement: Notifier Observes Backend Inbox Placement

The notifier SHALL use bounded observations of the backend's authoritative Inbox for eligible counts, compaction, and prompt content. At queued handoff it SHALL recheck current Inbox eligibility under the existing binding and readiness rules. Mail in backend Archive falls outside notifier work.

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
