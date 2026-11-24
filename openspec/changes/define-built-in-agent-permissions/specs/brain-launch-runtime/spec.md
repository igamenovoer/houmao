# Brain Launch Runtime Delta

## ADDED Requirements

### Requirement: Launch-Time Gateway Attach Requires Managed-Self Registration

For a new launch, the runtime SHALL commit the `managed-self` key and public binding together in the owner-private authorization database before native startup. Launch-time gateway attach SHALL verify that the binding belongs to the live current generation before advertising readiness or reporting combined success. A failure after agent startup SHALL follow the structured auto-attach failure contract.

#### Scenario: A profile launches an agent and its gateway

- **WHEN** the resolved launch profile starts Bob with launch-time gateway auto-attach
- **THEN** the owner runtime commits Bob's private key and matching public registration together before native startup
- **AND THEN** the gateway verifies the active binding before publishing ready state in either foreground or background execution
- **AND THEN** the registration leaves the selected administrator roster intact

#### Scenario: Registration is unavailable before combined readiness

- **WHEN** Bob's runtime starts but the launcher cannot validate the committed credential or the gateway cannot resolve its public registration before readiness
- **THEN** the launch reports a structured auto-attach error with Bob's live identity or manifest reference
- **AND THEN** Bob remains running without a gateway advertised as ready by the failed attempt
- **AND THEN** cleanup is limited to gateway resources created by that attempt

#### Scenario: A profile launches an agent with gateway auto-attach disabled

- **WHEN** the resolved profile starts Bob without a gateway
- **THEN** the owner runtime commits Bob's key and registration before native startup independently of any listener
- **AND THEN** a later attach can reuse his current verified registration

#### Scenario: A headless worker exits or a native process restarts

- **WHEN** Houmao verifies that a later turn or recovered process still belongs to Bob's same live managed generation
- **THEN** self commands can use the previously registered key from SQLite without a new registration
- **AND THEN** an authorized relaunch that creates a new generation provisions a fresh key
