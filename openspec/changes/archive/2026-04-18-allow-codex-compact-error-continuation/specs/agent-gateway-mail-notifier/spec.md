## ADDED Requirements

### Requirement: Mail notifier continues current context for recoverable degraded sessions
For prompt-ready sessions, recoverable degraded chat context SHALL NOT by itself cause an ordinary notifier busy skip and SHALL NOT by itself require clean-context notifier work.

When open inbox work is eligible and all existing readiness, notifier-mode, and queue-admission gates pass, the notifier SHALL enqueue or deliver the normal notifier prompt through current-context prompt work even if recoverable degraded context is present.

The notifier SHALL preserve explicit clean-context behavior only when a future caller-configured notifier policy or prompt-control request explicitly asks for clean context. It SHALL NOT infer that policy solely from recoverable degraded context.

Notifier audit records MAY include degraded-context detail for diagnostics, but SHALL NOT report clean-context outcomes unless a clean-context workflow actually ran.

#### Scenario: Prompt-ready degraded session gets notifier prompt
- **GIVEN** a gateway mail notifier has open inbox work for the managed session
- **AND GIVEN** the managed session is prompt-ready and its chat context is recoverably degraded
- **AND GIVEN** the notifier's existing queue-admission gates pass
- **WHEN** the notifier poll runs
- **THEN** the notifier enqueues or delivers the normal notifier prompt through current-context prompt work
- **AND THEN** the notifier does not record an ordinary busy skip solely because degraded context is present

#### Scenario: TUI notifier does not reset for degraded context alone
- **GIVEN** a TUI-backed gateway target is prompt-ready with recoverable degraded chat context
- **AND GIVEN** the notifier has eligible open inbox work
- **WHEN** the notifier poll creates notifier work
- **THEN** the notifier does not first send `/new`, `/clear`, or another context-reset signal solely because degraded context is present
- **AND THEN** the notifier audit outcome does not claim clean-context enqueue unless an explicit clean-context workflow ran

#### Scenario: Headless notifier does not force new chat for degraded context alone
- **GIVEN** a native headless gateway target has recoverable degraded chat context
- **AND GIVEN** the notifier has eligible open inbox work and all admission gates pass
- **WHEN** the notifier creates prompt work
- **THEN** the prompt work does not include `chat_session.mode = new` solely because degraded context is present
