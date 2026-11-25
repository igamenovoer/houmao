# Gateway Plugin API Spec Delta

## ADDED Requirements

### Requirement: Plugin Workers Can Observe Ordinary Prompt Readiness

The SDK SHALL expose a read-only ordinary prompt readiness signal to supervised workers under their current plugin context. The signal SHALL only advertise readiness for the current body and stop on context revocation. Dispatch SHALL still apply the host's authoritative readiness and identity checks for the specific event.

#### Scenario: An Agent Becomes Ready

- **WHEN** a supervised worker observes a transition to ordinary prompt readiness
- **THEN** it can consider submitting an event through the existing immediate dispatch operation
- **AND THEN** the observation itself reserves no admission and submits no work

#### Scenario: The Body Becomes Busy After a Ready Signal

- **WHEN** a worker submits an ordinary event after a ready observation and the body is busy at admission
- **THEN** dispatch returns the ordinary typed readiness error without submitting the event to the body or storing it for later admission

#### Scenario: The Host Revokes a Waiting Plugin Context

- **WHEN** a plugin context is revoked while its worker is observing readiness
- **THEN** the observation ends or fails explicitly and supplies no readiness from a replacement context

### Requirement: Ordinary Event Presentation Can Project Explicit Visible Fields

The SDK SHALL support an explicit agent-facing request projection for ordinary events. The host SHALL put the entire projection in one request fence below a trusted header. The header SHALL use host and validated binding context and direct the agent to apply its current rules and permissions. The host SHALL keep internal correlation separate and bound the entire rendered prompt before handoff.

#### Scenario: A Projected Event Contains Private Correlation Metadata

- **WHEN** a plugin submits a valid projection and includes internal event or binding metadata for host correlation
- **THEN** the visible envelope contains a host-written header and the projected fields within one host-owned request fence
- **AND THEN** the host keeps the internal identifiers and metadata outside the prompt

#### Scenario: Projected Text Resembles a Control or Envelope Field

- **WHEN** a projected content field includes gateway control text or characters resembling an envelope field or request fence delimiter
- **THEN** the host quotes those characters as data within the request fence and applies ordinary admission
- **AND THEN** the host renders only its own request fence boundary

#### Scenario: The Rendered Projection Exceeds the Limit

- **WHEN** a projection's final encoded prompt exceeds the gateway's finite event budget
- **THEN** validation fails explicitly before handoff and the agent receives no partial prompt
