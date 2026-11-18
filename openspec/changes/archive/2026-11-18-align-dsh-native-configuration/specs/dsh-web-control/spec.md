# dsh-web-control Specification

## ADDED Requirements

### Requirement: DSH Web Failures Surface Secret-Redacted Startup and Control Diagnostics

When a managed DSH Web Host fails during startup or returns an API control error during turn delivery, interruption, or relaunch, Houmao SHALL include a bounded, secret-redacted diagnostic summary from the supervisor exit record or Web API error payload in the surfaced failure detail. Launch tokens, session cookies, and resolved secret environment values SHALL remain excluded from surfaced diagnostics and public status payloads.

#### Scenario: Web Host Startup Failure Includes Sanitized Supervisor Reason
- **WHEN** a managed DSH Web Host exits before publishing verified bootstrap state and records a startup error
- **THEN** the launch failure includes a bounded, secret-redacted summary of the recorded startup failure rather than only a static generic message
- **AND THEN** launch tokens, cookies, and API keys are redacted if present

#### Scenario: Web Turn Control Failure Preserves Redacted Error Message
- **WHEN** the DSH Web control API returns a structured error during prompt admission, turn execution, interruption, or relaunch
- **THEN** Houmao surfaces both the error code and a bounded, secret-redacted error message in the resulting failure detail
