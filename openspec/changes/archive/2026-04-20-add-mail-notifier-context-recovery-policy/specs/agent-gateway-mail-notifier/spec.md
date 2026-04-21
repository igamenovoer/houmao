## ADDED Requirements

### Requirement: Gateway mail notifier exposes context recovery policy
Gateway mail notifier configuration SHALL include an explicit context-error policy and an explicit pre-notification context action.

The context-error policy SHALL support:

- `continue_current`, the default, which preserves current-context notifier delivery even when recoverable degraded chat context is present.
- `clear_context`, an opt-in policy that allows the notifier to start the notifier prompt from clean context when the current degraded diagnostic is a recognized compaction error for the owning CLI tool.

The pre-notification context action SHALL support:

- `none`, the default, which performs no context preflight before notifier prompt delivery.
- `compact`, an opt-in action that runs a supported CLI-tool-specific compaction preflight before notifier prompt delivery.

Notifier status responses SHALL report the effective context-error policy and pre-notification context action for enabled and disabled notifier states.

Existing notifier configurations that do not store these fields SHALL behave as `context_error_policy=continue_current` and `pre_notification_context_action=none`.

#### Scenario: Omitted context policies preserve current behavior
- **WHEN** a caller enables the mail notifier without specifying context recovery fields
- **THEN** the gateway stores or reports `context_error_policy=continue_current`
- **AND THEN** it stores or reports `pre_notification_context_action=none`
- **AND THEN** recoverable degraded context remains eligible for ordinary current-context notifier prompt delivery

#### Scenario: Status reports explicit context policies
- **WHEN** a caller enables the mail notifier with `context_error_policy=clear_context` and `pre_notification_context_action=compact`
- **THEN** subsequent notifier status responses report those effective values
- **AND THEN** the response does not require callers to infer policy from appendix text, logs, or audit rows

### Requirement: Pre-notification compaction runs only for supported CLI tools
When `pre_notification_context_action=compact` is configured, the notifier SHALL run a CLI-tool-specific compaction preflight before submitting the semantic mailbox notification prompt.

For Codex TUI-backed gateway targets, the v1 compaction preflight SHALL use Codex's interactive `/compact` command and wait for the tracked surface to return to prompt-ready posture before continuing.

For CLI tools or backend modes that do not define a supported notifier compaction preflight, notifier enablement or the first affected poll SHALL fail explicitly with a support error. The gateway SHALL NOT silently ignore the `compact` policy.

The compaction preflight SHALL be audited separately from mailbox prompt delivery. A failed compaction preflight SHALL NOT mark mail read, answered, moved, or archived.

#### Scenario: Codex TUI notifier compacts before notification
- **GIVEN** a Codex TUI-backed gateway target supports notifier compaction preflight
- **AND GIVEN** the mail notifier is configured with `pre_notification_context_action=compact`
- **AND GIVEN** eligible open inbox work exists
- **WHEN** the notifier poll reaches prompt delivery
- **THEN** the gateway submits Codex `/compact` before the mailbox notification prompt
- **AND THEN** it waits for prompt-ready posture before submitting the mailbox notification prompt
- **AND THEN** notifier audit records that a compaction preflight was attempted

#### Scenario: Unsupported compact policy fails explicitly
- **GIVEN** a gateway target has no supported notifier compaction preflight for its CLI tool and backend mode
- **WHEN** a caller configures or triggers `pre_notification_context_action=compact`
- **THEN** the gateway reports an explicit support error for that policy
- **AND THEN** it does not claim that pre-notification compaction is active or completed

#### Scenario: Failed compaction preflight does not mutate mailbox state
- **GIVEN** the notifier attempts a pre-notification compaction preflight
- **AND GIVEN** that preflight fails or produces a degraded compaction diagnostic
- **WHEN** the gateway records the notifier poll outcome
- **THEN** unread inbox mail remains unread unless mailbox state is changed through an explicit mailbox operation
- **AND THEN** the failed preflight does not move or archive any mailbox message

### Requirement: Mail notifier clears context only for explicit compaction-error policy
Recoverable degraded chat context SHALL NOT by itself cause mail-notifier clean-context recovery.

When `context_error_policy=clear_context` is configured and the current degraded diagnostic is a recognized compaction error for the owning CLI tool, the notifier SHALL use clean-context prompt delivery before submitting the semantic mailbox notification prompt.

When `context_error_policy=continue_current` is configured, the notifier SHALL use ordinary current-context delivery even if a recognized degraded compaction diagnostic is present, provided existing prompt-readiness and queue-admission gates pass.

When no recognized compaction-error diagnostic is present, `context_error_policy=clear_context` SHALL NOT clear context solely because generic current-error or degraded evidence exists.

#### Scenario: Default policy continues after Codex compaction error
- **GIVEN** a Codex TUI-backed gateway target is prompt-ready with a Codex-specific degraded compaction diagnostic
- **AND GIVEN** the notifier uses the default `context_error_policy=continue_current`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier submits the mailbox notification prompt through ordinary current-context delivery
- **AND THEN** it does not first send `/new`, `/clear`, or another context-reset signal

#### Scenario: Clear-context policy consumes recognized compaction error
- **GIVEN** a gateway target is prompt-ready with a recognized degraded compaction diagnostic for its owning CLI tool
- **AND GIVEN** the notifier is configured with `context_error_policy=clear_context`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier runs the supported clean-context workflow before submitting the mailbox notification prompt
- **AND THEN** notifier audit records that clean-context recovery was policy-selected

#### Scenario: Clear-context policy does not reset for generic error
- **GIVEN** a gateway target is prompt-ready with generic current-error evidence but no recognized compaction-error degraded diagnostic
- **AND GIVEN** the notifier is configured with `context_error_policy=clear_context`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier does not clear context solely because that generic error is visible
- **AND THEN** it either continues current-context delivery or records a non-compaction diagnostic according to the remaining readiness gates

### Requirement: Notifier audit records context policy decisions
Gateway notifier audit records SHALL include enough structured evidence to explain context policy behavior for each poll that reaches context preflight or prompt delivery.

The audit evidence SHALL identify:

- the effective context-error policy,
- the effective pre-notification context action,
- whether compaction preflight was attempted,
- whether clean-context recovery was attempted,
- the owning CLI tool for any degraded diagnostic,
- the tool-scoped degraded error type when present,
- the recovery outcome or failure detail.

Audit outcomes SHALL NOT claim clean-context notification success unless a clean-context workflow actually completed and the mailbox notification prompt was accepted afterward.

#### Scenario: Audit records ordinary current-context decision
- **GIVEN** the notifier is configured with default context policies
- **AND GIVEN** eligible open inbox work is delivered through current-context prompt work
- **WHEN** a caller inspects notifier audit history
- **THEN** the audit evidence identifies `context_error_policy=continue_current`
- **AND THEN** it identifies `pre_notification_context_action=none`
- **AND THEN** it does not claim clean-context recovery

#### Scenario: Audit records policy-selected recovery failure
- **GIVEN** the notifier is configured to clear context for recognized compaction errors
- **AND GIVEN** clean-context recovery fails before the mailbox notification prompt is accepted
- **WHEN** the gateway records the notifier poll
- **THEN** notifier audit records the recovery failure detail
- **AND THEN** it does not report the mailbox notification prompt as successfully enqueued after clean-context recovery
