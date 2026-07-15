## ADDED Requirements

### Requirement: Passive-server prompt proxy preserves admission-policy semantics

The maintained passive-server route `POST /houmao/agents/{agent_ref}/gateway/control/prompt` SHALL accept the schema-version-2 gateway prompt request, forward `admission_policy` unchanged to the live gateway, and return the live result or structured refusal without re-evaluating TUI readiness or pending input locally.

The proxy request SHALL NOT accept the removed `force` field, and its success and error projections SHALL expose the selected `admission_policy` instead of a boolean `forced` field.

#### Scenario: Managed-agent proxy forwards if-no-pending unchanged

- **WHEN** a caller sends a valid managed-agent gateway prompt request with `admission_policy=if_no_pending`
- **THEN** the passive server forwards that policy unchanged to the resolved live gateway
- **AND THEN** it returns the live gateway's admission result without applying a second local decision

#### Scenario: Pending refusal remains explicit through the proxy

- **WHEN** the live gateway refuses a proxied `if_no_pending` request because `surface.pending_input=yes`
- **THEN** the passive server returns the structured `pending_input` refusal explicitly
- **AND THEN** it does not convert the refusal into queued acceptance or a generic connectivity error

#### Scenario: Legacy force shape fails at the maintained proxy

- **WHEN** a caller submits the removed `force` field or prompt-control schema version 1 to the managed-agent proxy
- **THEN** strict request validation rejects the payload
- **AND THEN** the passive server does not translate the old shape before forwarding
