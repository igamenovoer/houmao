# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Uses an Already Prepared Installation

Houmao SHALL select one operator-configured Hermes root and qualified installed runtime in the selected execution context. Launch, relaunch, and prompt execution SHALL use the prepared dependency environment. Installation, dependency synchronization, and dependency changes SHALL require separate owner-authorized preparation.

#### Scenario: Fresh Workers Share Prepared Dependencies

- **WHEN** two workers launch from distinct projects in the same configured execution context
- **THEN** both use their own named profiles and the same prepared Hermes dependency environment
- **AND THEN** neither worker launch starts dependency installation, creates a private Python environment, or mutates the shared installation selection

#### Scenario: Prepared Installation Is Missing or Incompatible

- **WHEN** the configured installation is missing, stale, or lacks the required shared-profile, client, or caller-proof capabilities
- **THEN** Houmao fails preflight with the selected context and actionable preparation guidance
- **AND THEN** it leaves existing profiles, running workers, and project home links intact

#### Scenario: Worker Settings Require Unprepared Dependencies

- **WHEN** a worker's effective settings request a dependency unavailable in the prepared installation
- **THEN** launch refuses with owner-side preparation guidance before creating or replacing a worker binding

### Requirement: Managed Hermes Lifecycle Preserves Profile Attribution

Houmao SHALL scope native start, readiness, stop, relaunch, rollback, and recovery to the recorded profile on its qualified shared gateway. It SHALL apply credentials and the selected approval posture to that profile and verify their effective scope before readiness.

#### Scenario: Workers Use Different Credentials and Approval Modes

- **WHEN** two served profiles select different native settings, credentials, or approval postures
- **THEN** each uses its own selected inputs
- **AND THEN** an unavailable credential, approval mode, or profile binding fails explicitly without falling back to the root or a sibling profile
- **AND THEN** a native approval, file-edit grant, model change, or turn event only affects the profile and session for which it was established

#### Scenario: Stop and Relaunch Reuse an Owned Profile

- **WHEN** Houmao stops a worker whose home remains available for reuse
- **THEN** it closes that worker's admission, settles or reports unresolved owned work, and parks that profile
- **AND THEN** the home, workspace binding, and project link remain available for explicit relaunch
- **AND THEN** exact continuation requires verification of the saved session in that profile and workspace

#### Scenario: Concurrent Launch or Failed Publication

- **WHEN** launches share an owner root or a new launch fails after reserving a profile
- **THEN** Houmao serializes shared gateway acquisition and profile creation as required and publishes only verified worker bindings
- **AND THEN** rollback releases only the failed launch's acquired authority and artifacts and reports incomplete settlement

## MODIFIED Requirements

### Requirement: Hermes State and Configuration Belong to the Managed Agent

Houmao SHALL bind the selected agent to a distinct canonical Hermes named profile, separate native state, and explicit workspace. It SHALL project the role, selected skills, tool policy, model route, and privately referenced credentials into that profile while retaining the managed identity.

#### Scenario: Two Agents Have Separate Homes

- **WHEN** two managed Hermes agents launch under the same prepared execution-owner root
- **THEN** each binds its selected workspace and a separate named profile, session store, configuration, and credential source on the shared gateway
- **AND THEN** their runtime inputs and histories remain separately addressable

#### Scenario: A Managed Role and Skill Pack Are Selected

- **WHEN** an operator launches a managed agent from a profile with a role and managed skills
- **THEN** Hermes reads the effective role through its native identity input and discovers the selected skills through its own skill loader
- **AND THEN** Houmao's self-identity and gateway access reach the owned execution context and exact managed profile

#### Scenario: Browser and Desktop Control Are Excluded

- **WHEN** the managed Hermes launch uses its default tool posture
- **THEN** it exposes the qualified toolsets with browser and desktop-control tools excluded
- **AND THEN** startup and prompts do not acquire those optional binaries on demand

### Requirement: Hermes Lifecycle Verifies the Owned Native Authority

Houmao SHALL record and verify the execution owner, gateway incarnation, served profile identity and home, workspace, logical session, and managed generation. It SHALL attribute native work to that binding. Gateway detach or client loss SHALL preserve accepted work. Recovery SHALL reconcile existing work before reopening admission.

#### Scenario: Houmao Gateway Reattaches During an Accepted Turn

- **WHEN** the Houmao gateway restarts while the same managed Hermes profile remains available
- **THEN** the gateway recovers status through the same managed authority and does not dispatch another prompt
- **AND THEN** a terminal event from another profile, session, authority incarnation, or admission cannot settle the original request

#### Scenario: Hermes Restarts After Admission

- **WHEN** the shared Hermes gateway exits after accepting managed work
- **THEN** Houmao preserves the recorded admission and the distinction between queued and started work
- **AND THEN** recovery verifies the replacement gateway, exact served profile, and saved conversation before admitting new work
- **AND THEN** any native recovery of a persisted queue entry is observed as the original admission, while unresolved execution stays uncertain without a fresh managed submission

#### Scenario: Exact Relaunch Has No Matching Session

- **WHEN** the manager verifies a requested saved logical session and finds it missing or belonging to another profile, home, or workspace
- **THEN** the manager refuses exact continuation before submission
- **AND THEN** it does not move the workspace, select a recent conversation, or create a replacement conversation

#### Scenario: Operator Stops One of Two Managed Hermes Agents

- **WHEN** stop targets one named-profile worker on a shared gateway
- **THEN** Houmao verifies the targeted profile and its owned clients, settles the worker's active work or reports unresolved settlement, and retains the binding for explicit relaunch
- **AND THEN** the shared gateway and the other agent's profile, conversation, and terminal remain available

### Requirement: Hermes Daemon Ownership Follows the Managed Launch Home

The shared Hermes gateway SHALL run from the selected prepared root for the execution owner. Houmao SHALL establish or adopt only a verified gateway for that exact root and verify native service of the exact recorded named profile before granting worker authority. Worker lifecycle SHALL control the worker's own profile and clients.

#### Scenario: The Managed Home Has No Daemon

- **WHEN** Houmao needs native execution and the selected prepared root has no qualified gateway
- **THEN** it establishes one gateway for the root, verifies its identity, and binds the worker through that gateway
- **AND THEN** concurrent first launches converge on that same gateway

#### Scenario: A Daemon Is Already Running in the Managed Home

- **WHEN** Houmao finds a qualified gateway launched for the selected prepared root
- **THEN** Houmao reuses its verified process identity and separately verifies that the worker's recorded profile and required capabilities are served

#### Scenario: A Native Client Starts a Same-Home Replacement

- **WHEN** a native client starts a replacement gateway for the exact prepared root during attachment
- **THEN** Houmao verifies the replacement and makes each managed profile recover its own native authority before accepting new work
- **AND THEN** the old gateway's evidence cannot settle a new operation

#### Scenario: A Discovered Daemon Has a Different Launch Home

- **WHEN** discovery finds an unrelated gateway or a gateway whose launch root does not match the recorded prepared root
- **THEN** Houmao rejects that gateway for shared profile control and leaves it outside the managed lifecycle

#### Scenario: A Recorded Standalone Worker Is Retired

- **WHEN** an operator stops or explicitly cleans a Hermes worker recorded under the former standalone layout
- **THEN** Houmao uses the recorded standalone ownership and exact process identity
- **AND THEN** a request to continue that conversation in the new named-profile layout fails before stopping the predecessor or changing its home

### Requirement: Hermes Service Uses Persistent ACP

Hermes service mode SHALL own one persistent `hermes acp` client for the selected profile. It SHALL negotiate ACP and bind the exact logical session on the verified shared gateway before publishing readiness. Prompt settlement, reverse interactions, interruption, and edit policy SHALL remain scoped to the current operation and bound session.

#### Scenario: Two Prompts Use the Same ACP Service

- **WHEN** consecutive requests are admitted to the same healthy service
- **THEN** both use the same ACP process, verified gateway incarnation, profile, and bound session
- **AND THEN** resume-time replay remains historical evidence

#### Scenario: ACP Requests an Approval

- **WHEN** the peer asks for a tool approval during a turn
- **THEN** the owner responds using the authorized native policy and an advertised option while it continues to drain protocol output
- **AND THEN** unqualified client facilities or unanswered user interactions do not silently grant access

#### Scenario: Unattended Service Establishes the Broadest Qualified Native Edit Mode

- **WHEN** an unattended service starts or explicitly relaunches and verifies its ACP session
- **THEN** the owner confirms the broadest qualified native edit mode on that session before publishing readiness
- **AND THEN** ordinary supported file edits can proceed with the full scope that Hermes permits for the selected execution identity
- **AND THEN** a peer that cannot establish that mode produces an explicit compatibility failure

#### Scenario: An Unattended Tool Permission Is Attributable

- **WHEN** an unattended ACP peer sends a supported tool-permission request for the bound profile, session, and current uncancelled operation
- **AND WHEN** the request offers one qualifying one-time allow option with an unambiguous option identifier
- **THEN** Houmao selects that advertised one-time option while continuing to drain the active turn
- **AND THEN** the response creates no persistent grant and preserves native hard denials

#### Scenario: ACP Cannot Authorize the Reverse Interaction

- **WHEN** a reverse interaction concerns another profile or session, concerns a cancelled or inactive operation, lacks a qualifying permission request or option, or asks for clarification, model or provider change, or another non-tool decision
- **THEN** Houmao leaves it ungranted using the applicable refusal or cancellation response
- **AND THEN** Houmao supplies no fabricated answer or consent

#### Scenario: As-Is Service Leaves Native Approval in Effect

- **WHEN** the selected ACP launch requests `as_is`
- **THEN** the owner preserves the selected native edit mode and does not apply unattended automatic tool grants

#### Scenario: ACP Disconnects During Work

- **WHEN** the ACP process or stream disappears after a prompt may have been submitted
- **THEN** the owner reports uncertainty until it verifies the exact profile's native outcome
- **AND THEN** viewer exit is insufficient evidence of cancellation
