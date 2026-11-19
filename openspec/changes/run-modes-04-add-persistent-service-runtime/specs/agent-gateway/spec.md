# Spec Delta

## MODIFIED Requirements

### Requirement: DSH ACP Agents Support Managed Gateway Operations

Runtime-owned DSH ACP agents SHALL support gateway attach, detach, semantic prompt, interruption, status, canonical events, and shared usage access through the persistent service owner. Readiness SHALL reflect the verified ACP connection, bound session, and active execution throughout the service lifetime.

#### Scenario: Gateway Attaches Between DSH Turns
- **WHEN** the managed DSH service owner has an initialized ACP connection and an idle bound session
- **THEN** gateway attach succeeds and exposes the agent's actual idle or unavailable posture

#### Scenario: DSH Work Is Already Active
- **WHEN** an ordinary plugin event arrives while DSH has an active managed turn
- **THEN** the gateway returns an immediate retryable conflict
- **AND THEN** no plugin payload enters a delayed queue or overlapping ACP request

#### Scenario: Gateway reattaches with the service down

- **WHEN** the supervisor exists but its ACP connection was lost
- **THEN** the gateway reports native control unavailable and does not start a replacement provider to answer a read

### Requirement: DSH Mail and Plugin Integrations Reuse Core Admission

Mail reminders, CCCC chat, explicit deferred-message consumption, and other plugins targeting a qualified DSH headless, service, or Web agent SHALL use the existing owner-bound semantic dispatch and shared core admission. Adding DSH SHALL NOT create another mailbox identity, bypass delivery selection, or change existing periodic reminder semantics.

#### Scenario: An Eligible Mail Reminder Wakes a DSH Agent
- **WHEN** an existing mailbox notifier finds eligible work while the DSH agent is ready
- **THEN** its notification uses ordinary managed semantic dispatch
- **AND THEN** unchanged inbox work retains the configured periodic reminder behavior

#### Scenario: A Plugin Calls the DSH Agent Through Its Owner
- **WHEN** an enabled owner-bound plugin delivers an event to the DSH gateway
- **THEN** existing plugin ownership, readiness, and execution-generation checks remain in force

#### Scenario: A service is disconnected at dispatch

- **WHEN** an ordinary reminder or plugin wake targets a DSH owner without a verified ACP connection
- **THEN** core admission reports the unavailable target and does not enqueue a later native prompt
