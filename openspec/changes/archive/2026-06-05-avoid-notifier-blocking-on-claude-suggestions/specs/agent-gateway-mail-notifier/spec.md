## ADDED Requirements

### Requirement: Gateway notifier readiness honors style-classified Claude suggestions

For TUI-backed gateway targets, the mail notifier SHALL continue using the tracked prompt-readiness contract to decide whether notifier prompt enqueueing is safe.

When eligible inbox work exists, queue admission gates pass, and the tracked state reports ready posture because the only visible Claude prompt payload is a style-classified ghost suggestion, the notifier SHALL NOT defer solely because stripped prompt text is non-empty.

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
