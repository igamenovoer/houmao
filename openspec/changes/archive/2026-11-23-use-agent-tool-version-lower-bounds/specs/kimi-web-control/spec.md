# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi Web binds one native browser and control session

A `(kimi, web)` launch SHALL admit eligible Kimi Code builds at or above 2.6.0 and start `kimi web --no-open` in the selected private home and execution context. Before declaring readiness, the owner SHALL verify the expected host, listener, native API, session, and workspace. Public discovery SHALL expose a token-free browser handoff.

#### Scenario: Browser and gateway use the same conversation

- **WHEN** a person opens the verified native session and an authorized gateway addresses that session
- **THEN** both observe the same native conversation and retain independent client lifetimes

#### Scenario: The port belongs to another process

- **WHEN** the listener or host fails verification
- **THEN** the owner reports unavailable and withholds credentials and control input

#### Scenario: A newer Kimi Web build passes verification

- **WHEN** Kimi Code 2.7.2 or a later eligible build provides the required native API and verified session
- **THEN** the owner publishes readiness for the bound session

#### Scenario: A newer build lacks the expected Web API

- **WHEN** an eligible build fails native Web verification
- **THEN** launch identifies the failed startup check and withholds readiness
