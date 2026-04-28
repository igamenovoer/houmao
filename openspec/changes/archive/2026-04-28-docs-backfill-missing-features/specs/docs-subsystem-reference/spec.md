## ADDED Requirements

### Requirement: Registry reference documents lifecycle-aware recovery

The registry reference SHALL document that lifecycle-aware records track `active`, `stopped`, `relaunching`, and `retired` states, and that recovery operations transition records between these states when tmux inspection reveals degraded or stale sessions. The registry reference SHALL link to the degraded-stale recovery page from the discovery-and-cleanup section.

#### Scenario: Reader understands registry state transitions during recovery

- **WHEN** a reader reads the registry reference
- **THEN** they understand that recovery may transition an `active` record to `stopped` or `retired` depending on probe classification and operator intent
- **AND THEN** they can follow a link to the recovery page for the full probe and routing model

### Requirement: Gateway reference documents degraded-context handling

The gateway reference SHALL mention that the gateway notifier's degraded-context handling (`context_error_policy` and `pre_notification_context_action`) interacts with recovery: a degraded tmux session may trigger the gateway's degraded-context path before recovery runs. The gateway reference SHALL cross-reference the recovery page.

#### Scenario: Reader understands gateway interaction with recovery

- **WHEN** a reader reads the gateway mail-notifier or protocol reference
- **THEN** they see a note that degraded tmux posture can arise from broken sessions that recovery addresses
- **AND THEN** they can follow a link to the recovery page
