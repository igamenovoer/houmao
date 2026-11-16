# Spec Delta

## ADDED Requirements

### Requirement: DSH ACP Agents Support Managed Gateway Operations

Runtime-owned DSH ACP agents SHALL support gateway attach, detach, semantic prompt, interruption, status, canonical events, and shared usage access through the maintained headless contract. Readiness SHALL describe the resumable logical agent and active execution, without requiring a worker process between turns or inventing terminal-parser state.

#### Scenario: Gateway Attaches Between DSH Turns
- **WHEN** the managed DSH headless envelope is live and resumable with no active worker
- **THEN** gateway attach succeeds and exposes the agent's actual idle or unavailable posture

#### Scenario: DSH Work Is Already Active
- **WHEN** an ordinary plugin event arrives while DSH has an active managed turn
- **THEN** the gateway returns an immediate retryable conflict
- **AND THEN** no plugin payload enters a delayed queue or overlapping ACP process

### Requirement: DSH Immediate Dispatch Is Fenced at Native Handoff

An immediate DSH event attempt SHALL bind its dispatch permission to the captured managed generation and native execution. Native admission evidence SHALL belong to that attempt. Expiry, caller loss before handoff, provider failure, or execution replacement SHALL revoke the attempt and report failure or uncertainty without retaining authority to resend its payload.

#### Scenario: The Driver Starts but DSH Rejects the Prompt
- **WHEN** the helper launches but initialization, session selection, or native prompt admission fails
- **THEN** the gateway returns a dispatch error rather than treating helper process creation as successful handoff

#### Scenario: The Managed Generation Changes Before Input
- **WHEN** an event passes initial checks but its captured execution generation changes before native input is submitted
- **THEN** the attempt fails and its prompt is not sent to the replacement generation

#### Scenario: Provider Failure Follows Native Admission
- **WHEN** DSH admits the prompt but exits or restarts before the pending operation reaches a confirmed terminal result
- **THEN** the pending response or recorded result reports failure or uncertainty
- **AND THEN** neither gateway recovery nor later readiness resends the original prompt

### Requirement: DSH Mail and Plugin Integrations Reuse Core Admission

Mail reminders, CCCC chat, explicit deferred-message consumption, and other plugins targeting a DSH headless agent SHALL use the existing owner-bound semantic dispatch and shared core admission. Adding DSH SHALL NOT create another mailbox identity, bypass delivery selection, or change existing periodic reminder semantics.

#### Scenario: An Eligible Mail Reminder Wakes a DSH Agent
- **WHEN** an existing mailbox notifier finds eligible work while the DSH agent is ready
- **THEN** its notification uses ordinary managed semantic dispatch
- **AND THEN** unchanged inbox work retains the configured periodic reminder behavior

#### Scenario: A Plugin Calls the DSH Agent Through Its Owner
- **WHEN** an enabled owner-bound plugin delivers an event to the DSH gateway
- **THEN** existing plugin ownership, readiness, and execution-generation checks remain in force
