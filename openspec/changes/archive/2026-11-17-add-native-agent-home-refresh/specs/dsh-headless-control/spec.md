# Spec Delta

## MODIFIED Requirements

### Requirement: DSH Operation Support Is Explicit

DSH headless capability inspection SHALL identify supported creation, exact resume, prompting, cancellation, closure, native prompt, skills, accounting sources, common-plugin observation, and home refresh. Qualified skills/MCP discovery SHALL remain distinct from ACP wire reload. Unsupported load, transcript replay, deletion, fork, additional-workspace, raw-key, or ACP reload SHALL fail explicitly without emulation through ordinary chat.

#### Scenario: Caller Requests Unsupported Session Fork
- **WHEN** a caller requests a DSH operation that the qualified ACP implementation does not support
- **THEN** Houmao reports that operation as unsupported without creating another native session

#### Scenario: Profile Files Change During a Turn
- **WHEN** DSH profile files change while a managed headless turn is active
- **THEN** Houmao does not claim coordinated live activation merely because the files changed

#### Scenario: Qualified Home Refresh Needs No ACP Request
- **WHEN** an active DSH envelope has qualified next-invocation skills/MCP discovery and receives home refresh between workers
- **THEN** refresh reports an automatic future-boundary result without creating an ACP process or sending an ACP reload request
- **AND** it does not claim that a worker's live common state has already been inspected

#### Scenario: Unsupported Native Reload Remains Explicit
- **WHEN** a caller requests an ACP wire reload that the selected native implementation does not support
- **THEN** the operation remains unsupported even if Houmao can report automatic home discovery on the next invocation
- **AND** no ordinary chat message is used to emulate the missing wire operation

## ADDED Requirements

### Requirement: DSH Turn Preparation Preserves Current Materialized Home Inputs

Ordinary DSH ACP invocation SHALL consume current materialized native inputs, including skills/MCP, without regenerating profile, role, or persistent configuration from launch manifests. Per-attempt control and evidence SHALL remain private transient inputs. Native precedence SHALL remain explicit and launch/relaunch SHALL retain their separate materialization rules.

#### Scenario: Native Configuration Was Edited Before the Next Turn
- **WHEN** an operator edits the materialized DSH profile or supported MCP declarations and later submits an ordinary prompt after qualified automatic refresh
- **THEN** that invocation consumes the current native home according to native precedence
- **AND** turn preparation does not restore the preceding launch-generated profile or MCP declaration

#### Scenario: Launch Profile Changed Without Relaunch
- **WHEN** the stored Houmao launch profile changes after a DSH home has been materialized
- **AND** the caller invokes native-home refresh and then submits an ordinary prompt
- **THEN** refresh and turn preparation preserve the current materialized role and profile bytes
- **AND** they do not recompose a new system prompt from the edited launch profile

#### Scenario: Required Materialized Input Was Removed
- **WHEN** a caller removes a required materialized native input before the next ACP invocation
- **THEN** native validation fails explicitly if that input is required
- **AND** the invocation does not repair it by regenerating launch material or creating a different conversation

### Requirement: DSH Automatic Home Discovery Preserves Native Continuity

Qualified next-invocation skills/MCP discovery SHALL preserve exact native conversation, dispatch, credential-isolation, and usage contracts. Refresh SHALL neither replay input nor restart an active attempt. Common limitations SHALL remain explicit; unrelated pending native-special-plugin changes SHALL NOT invalidate confirmed common discovery.

#### Scenario: Skills Are Added Updated and Removed Between Workers
- **WHEN** a caller adds, edits, or removes skills in one DSH native home and requests qualified automatic refresh
- **THEN** the next ordinary invocation discovers that home's current skill state in the same selected conversation
- **AND** the refresh itself launches no worker and changes no other agent's home

#### Scenario: Current ACP Attempt Is Still Running
- **WHEN** home refresh is requested while an ACP attempt is active
- **THEN** a qualified automatic result refers only to its later native boundary, or an unsupported live action is refused explicitly
- **AND** the active attempt is not interrupted, restarted, replayed, or replaced

#### Scenario: Explicit Invocation Overrides Are Present
- **WHEN** a subsequent ordinary DSH invocation has supported request-scoped model controls
- **THEN** those controls retain their documented temporary precedence without rewriting persistent home files
- **AND** exact continuation, dispatch fencing, and accounting remain bound to the original managed authority

### Requirement: DSH Headless Observation Does Not Fabricate Live Freshness

DSH headless observation SHALL identify common coverage, evidence, and native boundaries independently of Houmao update receipts. Between workers it SHALL report qualified future behavior and unavailable live evidence explicitly. Automatic native updates SHALL be accepted, while unknown coverage SHALL NOT justify an already-current no-op.

#### Scenario: No ACP Worker Is Live
- **WHEN** a valid headless envelope is inspected between invocations
- **THEN** the result distinguishes current-input evidence from qualified next-turn discovery and unavailable live-worker observations
- **AND** no worker is started to manufacture evidence

#### Scenario: Native Update Has No Houmao Receipt
- **WHEN** external or native tooling changes DSH skills/MCP outside Houmao
- **THEN** observation evaluates available effective-input/runtime evidence without requiring a Houmao update record

#### Scenario: Launch Overlay Masks a Common Edit
- **WHEN** a retained invocation override prevents an edited common input from taking effect
- **THEN** the result exposes that precedence limitation or unknown coverage
- **AND** it does not infer current common state merely from the edited file's presence

#### Scenario: A Read Would Require Forced Native Work
- **WHEN** complete freshness would require starting ACP or issuing a mutating refresh request
- **THEN** the read-only observation preserves the evidence limitation instead of performing that work
