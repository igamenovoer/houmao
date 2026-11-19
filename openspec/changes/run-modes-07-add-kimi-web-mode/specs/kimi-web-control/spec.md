# Spec Delta

## Purpose

Specify Kimi Web as one managed native browser host with authenticated gateway control, race-safe admission, and exact session and prompt identity.

## ADDED Requirements

### Requirement: Kimi Web binds one native browser and control session

A qualified `(kimi, web)` launch SHALL start `kimi web --no-open` in the selected private native home and execution context. The owner SHALL verify the expected host incarnation, endpoint, authenticated native session, and workspace before declaring control ready. Public discovery SHALL expose only a non-secret, operator-usable browser or connection handoff.

#### Scenario: Browser and gateway use the same conversation

- **WHEN** a human opens the verified native session and the gateway connects with its own authorized client
- **THEN** both observe the same native conversation while their client lifecycles remain independent

#### Scenario: The port belongs to a replacement host

- **WHEN** the supervisor still exists but the listener, home, or session binding fails verification
- **THEN** the owner reports unavailable and sends neither credentials nor control input to the unexpected host

### Requirement: Ordinary Kimi Web input uses conditional native admission

Ready-only prompts, mail wakeups, and plugin input SHALL use an atomic native decision bound to host, session, generation, and readiness at submission. Losing a race SHALL leave no queued input, cold activation, model change, or other prompt side effect. Every native input path, including the browser, SHALL participate in the same admission decision for the managed request.

#### Scenario: A browser wins after the gateway's readiness read

- **WHEN** a human starts a turn before an ordinary managed submission reaches its native mutation boundary
- **THEN** the managed caller receives a conflict and its prompt and overrides are never applied, queued, or replayed

#### Scenario: Only unconditional submission exists

- **WHEN** the native host cannot provide a qualified conditional submission covering preparation and enqueue
- **THEN** the managed Web selection reports unsupported before admitting work or publishing a supported surface

#### Scenario: A caller explicitly requests queueing

- **WHEN** a busy agent receives a submission requesting delayed delivery
- **THEN** only a separately qualified explicit queue operation may enqueue it and its receipt identifies queued status

### Requirement: Observation and interruption address attributable Web work

Kimi Web inspection SHALL preserve native origin, session and prompt identity. Reads SHALL avoid cold activation and other mutations. Managed interruption SHALL target the exact verified prompt. Human work, ambiguous output, and accepted cancellation SHALL retain their actual evidence and SHALL NOT settle a different managed request.

#### Scenario: The human starts a browser turn

- **WHEN** the gateway observes a native prompt outside any managed submission
- **THEN** its output is recorded only with the available human or external origin and cannot settle or be canceled as an unrelated managed turn

#### Scenario: Ordinary inspection sees a cold session

- **WHEN** the stock state route would resume the session as a side effect
- **THEN** inspection returns last-known or unavailable evidence and leaves the session cold

#### Scenario: A connection drops after submission

- **WHEN** the native host may have accepted a correlated request but the client loses its response
- **THEN** the owner reconciles against the same host, session and prompt identity or reports uncertainty without resubmission

### Requirement: Gateway lifecycle preserves private Web access

Gateway reattachment SHALL use the verified existing Web host and exact session. Operator stop and relaunch SHALL fence old handles and obey the owner lifecycle contract. Native credentials, access-bearing query or fragment data, and private API endpoints SHALL stay outside public handoff, shared records, and logs.

#### Scenario: Gateway is replaced while a browser stays open

- **WHEN** a new authenticated gateway attaches while the same Kimi host and session remain live
- **THEN** browser work continues and the gateway uses independent credentials or client state scoped to the owner

#### Scenario: Relaunch selects saved continuity

- **WHEN** the previous Web host has stopped and the operator requests its session on relaunch
- **THEN** the owner verifies the new host and exact saved session before allowing new work and rejects stale prompt handles
