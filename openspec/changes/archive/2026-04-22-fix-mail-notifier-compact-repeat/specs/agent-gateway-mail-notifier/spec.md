## ADDED Requirements

### Requirement: Pre-notification compaction runs at most once per continuously eligible mail item
When `pre_notification_context_action=compact` is configured, the gateway mail notifier SHALL treat compaction as a one-shot preflight for each mail item's current eligibility stretch rather than as an action that repeats on every later notifier cycle.

For this requirement, a mail item's eligibility stretch lasts only while that message remains eligible for the notifier's current mode:

- in `any_inbox`, while the message remains an unarchived inbox item,
- in `unread_only`, while the message remains unread and unarchived in the inbox.

The notifier SHALL remember which currently eligible `message_ref` values have already triggered successful pre-notification compaction during their current eligibility stretch.

When a later notifier cycle sees only previously remembered eligible mail, the notifier MAY still enqueue or deliver the semantic mailbox wake-up prompt according to the existing readiness and queue-admission rules, but it SHALL NOT run another pre-notification compaction solely because that same eligible mail remains present.

When a later notifier cycle sees at least one newly eligible mail item that has not yet triggered compaction during its current eligibility stretch, the notifier SHALL run at most one additional compaction preflight for that cycle before continuing with ordinary notifier prompt behavior.

When a previously remembered mail item leaves the eligible set, the notifier SHALL forget that remembered compaction state for that item so a future re-entry into eligibility begins a new eligibility stretch.

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
- **AND GIVEN** `A` later becomes ineligible because it is no longer unread or no longer in the eligible inbox set
- **WHEN** `A` later becomes eligible again in a new eligibility stretch
- **THEN** the notifier may run one fresh pre-notification compaction for `A`
- **AND THEN** it does not treat the earlier eligibility stretch as permanent suppression
