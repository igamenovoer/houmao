# Hermes Agent Runtime Specification

## Purpose

Define how Houmao builds, launches, controls, and observes managed Hermes agents in terminal, persistent service, and finite CLI modes.

## Requirements

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

### Requirement: Hermes TUI Uses Native Structured Control

Hermes TUI mode SHALL expose a real Hermes terminal through tmux and use verified native RPC for manager and gateway control. Houmao SHALL pin the exact logical conversation and report terminal attachment separately from native availability. Readiness, turns, and completion SHALL derive from structured evidence.

#### Scenario: Native TUI and Houmao Share One Conversation

- **WHEN** an operator attaches to the pane and sends a turn in the verified conversation
- **THEN** Houmao observes native activity for that session without capturing terminal text
- **AND THEN** later Houmao submissions and corresponding native events appear in the same conversation

#### Scenario: Human Switches or Exits the TUI

- **WHEN** the operator changes the TUI's displayed conversation or closes the TUI client
- **THEN** Houmao reports the changed terminal attachment alongside the original managed conversation
- **AND THEN** automated input and accepted work remain addressed to the pinned conversation
- **AND THEN** changing the managed conversation requires an explicit verified lifecycle or session operation

#### Scenario: Parser-Specific Operations Target Hermes

- **WHEN** a caller requests terminal-parser history, automatic key dispatch, or another parser-specific operation from a Hermes TUI
- **THEN** the operation reports unsupported
- **AND THEN** qualified terminal handoff and structured control remain available

#### Scenario: A Direct Manager Prompt Uses the Native Owner

- **WHEN** a local or delegated manager prompt selects a current Hermes TUI generation with a ready pinned conversation
- **THEN** the manager and gateway use the same owner admission and Hermes native submit path
- **AND THEN** the manager correlates its result to its original owner claim and exact durable native admission
- **AND THEN** submission and settlement work when the gateway is detached or Ink is absent or displaying another conversation

#### Scenario: Manager and Gateway Compete for the Owner Slot

- **WHEN** a manager prompt and a gateway prompt compete for the same pinned conversation and managed generation
- **THEN** the shared owner slot admits at most one prompt while its outcome remains unresolved
- **AND THEN** the refused caller reports that work is outstanding before sending input

#### Scenario: Manager Wait Reports Exact Terminal or Known Admission Evidence

- **WHEN** the manager waits for a submitted Hermes TUI prompt
- **THEN** it reports completion, failure, or interruption only from a terminal receipt attributable to that request
- **AND THEN** if its bounded wait expires with verified queue acceptance or native handoff, it reports that acceptance under the original request ID
- **AND THEN** if admission cannot be established, it reports uncertainty and retains the evidence for reconciliation without replaying the prompt

#### Scenario: A Direct Manager Prompt Finds the Pinned Conversation Busy

- **WHEN** the pinned conversation is busy at the final native readiness check or the selected owner is unavailable
- **THEN** the manager reports the native refusal or unavailable authority before sending input
- **AND THEN** a failed pre-admission attempt does not leave an unresolved slot that prevents the next qualified prompt

### Requirement: Hermes TUI Preserves Queued Receipts After the Idle Check

For an ordinary Hermes TUI prompt, Houmao SHALL check fresh native session readiness immediately before submit. The owner SHALL serialize its managed callers, use one stable input identity, and retain a verified native queue receipt even if a human input wins the race.

#### Scenario: Session Is Busy at the Check

- **WHEN** the pinned conversation has an active turn, pending interaction, pending work, or unresolved outcome at the submission check
- **THEN** Houmao defers or refuses according to the existing caller contract before it sends anything to Hermes

#### Scenario: Human Input Wins After the Check

- **WHEN** Houmao observes the pinned conversation ready and a human input reaches Hermes first
- **AND WHEN** Hermes accepts the managed prompt and returns a queued receipt
- **THEN** Houmao records the native admission as queued and leaves it with Hermes
- **AND THEN** Houmao neither sends a second prompt nor waits for an artificial idle transition before recognizing handoff
- **AND THEN** the human turn's events and completion cannot settle the managed prompt

#### Scenario: Fresh Submission Receives an Initial Queued Receipt

- **WHEN** a fresh prompt is accepted into Hermes's queue even though no human turn was active at the check
- **THEN** the response records durable queue acceptance and advances to started only on attributable native evidence

#### Scenario: Native Acknowledgment Is Lost

- **WHEN** transport loss leaves the submit acknowledgment unresolved
- **THEN** recovery uses the original principal, home, session, input identity, and exact payload to recover the same admission when qualified
- **AND THEN** a lost event, a missing pending-list row, or a matching prompt string alone cannot prove acceptance or completion
- **AND THEN** an unresolved attempt stays uncertain

#### Scenario: Native Queue Entry Is Cancelled or Changed

- **WHEN** an authorized control cancels, replaces, or steers the queued admission
- **THEN** Houmao reports the attributable native disposition and does not claim an independent completed turn from another admission

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

### Requirement: Hermes Headless Uses a Finite Structured CLI Client

Every accepted Hermes headless turn SHALL use one finite `hermes chat` CLI client with literal input and structured JSONL output. Houmao SHALL verify the exact named profile, logical session ID, and workspace before continuation. It SHALL select that profile and pass the ID unchanged to stock `--resume`, which uses Hermes's native lookup behavior. Houmao SHALL retain raw turn artifacts and publish attributable semantic events separately.

#### Scenario: Two Headless Prompts Continue the Same Session

- **WHEN** the second prompt explicitly continues the first native conversation and Hermes resolves the verified ID
- **THEN** Houmao starts `hermes --profile <profile> chat` with `--resume <full-id>` in the verified workspace
- **AND THEN** the model sees the earlier turn and the client accepts multiline input literally

#### Scenario: The CLI Reports a Different Session After Verification

- **WHEN** the verified ID disappears before the CLI looks it up and the native title fallback selects another conversation
- **THEN** Houmao treats any result identifying the different logical session as insufficient to settle the requested turn
- **AND THEN** the requested conversation remains the managed binding

#### Scenario: Terminal JSONL Supplies Completion

- **WHEN** the CLI stream closes with a valid terminal result whose session and exit agree with the tracked turn
- **THEN** Houmao settles the request and publishes the attributable output
- **AND THEN** the final response replaces incomplete text deltas when Hermes reports a replay gap

#### Scenario: CLI Exits While Status Is Ambiguous

- **WHEN** the CLI disappears, emits an incomplete or ambiguous result, or exits after merely detaching
- **THEN** Houmao keeps the native execution unresolved until it can verify the exact receipt or establish a definitive pre-admission failure
- **AND THEN** it neither opens a second turn slot nor retries the prompt due to the CLI exit

#### Scenario: Interrupt Targets a Qualified Headless Admission

- **WHEN** an interrupt names the current managed turn and Houmao can prove its exact native admission
- **THEN** cancellation targets only that admission and remains pending until native settlement
- **AND THEN** a stale interrupt or a missing attribution produces an explicit refusal without cancelling other work

### Requirement: Hermes Exposes Only Qualified Semantic Evidence

Houmao SHALL project native state, assistant output, tool progress, outcomes, and usage with the verified correlation that the selected Hermes mode provides. Terminal detail, duplicate events, session history, and cumulative usage SHALL retain their own semantics.

#### Scenario: Per-Turn Usage Cannot Be Established

- **WHEN** Hermes reports session-cumulative counters, context occupancy, or placeholder zeros without attributable per-turn measurements
- **THEN** usage remains unknown or explicitly incomplete for that Houmao turn

#### Scenario: Private Hermes Data Is Encountered During Observation

- **WHEN** a caller views launch output, diagnostics, state, events, or a managed receipt
- **THEN** the response omits raw native endpoints, tickets, credentials, and unauthorized native artifacts
- **AND THEN** it identifies the bound managed and native operation using safe references
### Requirement: Hermes TUI recovery settles only from valid durable evidence
A durable Hermes TUI receipt SHALL settle an owner prompt attempt only when it satisfies the receipt contract and can be attributed to that attempt and its recorded managed authority. An incomplete, malformed, or mismatched receipt SHALL leave the attempt unresolved until valid attributable evidence settles it or authorized lifecycle recovery fences it.

#### Scenario: Incomplete terminal evidence cannot release admission
- **WHEN** owner recovery sees a receipt with a terminal outcome and matching apparent identifiers but missing required receipt fields
- **THEN** the receipt does not settle the prompt or release the unresolved owner slot
- **AND THEN** recovery does not replay the prompt

#### Scenario: Valid terminal evidence settles the matching attempt
- **WHEN** a complete durable receipt proves a terminal outcome for the exact owner attempt
- **THEN** recovery settles that attempt according to the recorded outcome

#### Scenario: A queued receipt stays queued
- **WHEN** a complete receipt proves that the native session queued the prompt
- **THEN** recovery retains the original admission and its queued status until attributable evidence changes it

### Requirement: Managed Hermes Applies the Maximum Qualified Unattended Approval Posture

At managed start and explicit relaunch, Houmao SHALL establish the maximum qualified native approval posture for the selected unattended Hermes mode and verified home. Native hard denials and authority checks SHALL remain in effect. Unsupported approval behavior SHALL fail explicitly before readiness. `as_is` SHALL preserve the selected native approval policy.

#### Scenario: Unattended TUI Runs an Approval-Gated Command Without an Operator

- **WHEN** a fresh or explicitly relaunched unattended Hermes TUI runs a tool action that normally requires recoverable command approval
- **THEN** the verified native execution applies the unattended approval policy without waiting for an operator or an attached Ink viewer
- **AND THEN** attempts covered by native hard denials still fail

#### Scenario: Unattended Headless Continues the Verified Conversation

- **WHEN** an unattended finite Hermes turn executes in a fresh or explicitly relaunched managed runtime
- **THEN** the finite client uses its qualified unattended command-approval policy and the verified exact conversation
- **AND THEN** both the first turn and an exact continuation can execute an otherwise approval-gated command without human input

#### Scenario: Unattended Service Preserves Its Native Command-Approval Posture

- **WHEN** a fresh or explicitly relaunched unattended Hermes service executes a tool action normally subject to recoverable command approval
- **THEN** the verified native execution applies the unattended approval policy without waiting for an operator
- **AND THEN** native hard denials remain in effect and other managed agents retain their own approval policies

#### Scenario: As-Is Start Uses the Selected Native Policy

- **WHEN** the selected Hermes launch requests `as_is`
- **THEN** the start or explicit relaunch uses the selected native approval policy without retaining Houmao-generated unattended settings as authored policy

#### Scenario: Observation Leaves the Live Approval Policy Intact

- **WHEN** an authorized caller observes or controls an already-live Hermes runtime without requesting explicit lifecycle start or relaunch
- **THEN** the operation leaves the managed approval posture intact

### Requirement: Hermes TUI Reports Pending Native Approval

Houmao SHALL expose a safe optional `control.approval_pending` indicator from current structured approval evidence for the exact managed Hermes TUI session and execution. A verified pending approval SHALL keep the turn active and new prompt admission closed. The indicator SHALL omit the approval payload and remain unknown when the evidence is unavailable or invalid.

#### Scenario: A Manual Approval Remains Pending With Ink Detached

- **WHEN** the verified native execution for an `as_is` managed TUI awaits recoverable tool approval
- **THEN** manager, gateway, and passive-server state report pending approval and closed prompt admission independently of the Ink attachment
- **AND THEN** the response omits the native command, description, option values, file content, and other private approval data

#### Scenario: Native Settlement Clears the Pending Indicator

- **WHEN** current native evidence confirms the approval is resolved or withdrawn
- **THEN** state reports `control.approval_pending` as false and derives readiness from the remaining native work

#### Scenario: Other Prompts and Stale Approval Evidence Are Excluded

- **WHEN** native state contains a clarification, a queued prompt, or an approval from another execution generation
- **THEN** that evidence alone does not establish a pending approval for the managed execution
- **AND THEN** an unverified session or malformed approval evidence leaves the indicator unknown

### Requirement: Managed Hermes Uses an Already Prepared Installation

Houmao SHALL select one operator-configured Hermes root and qualified installed runtime in the selected execution context. Launch, relaunch, and prompt execution SHALL use the prepared dependency environment. Installation, dependency synchronization, and dependency changes SHALL require separate owner-authorized preparation.

#### Scenario: Fresh Workers Share Prepared Dependencies

- **WHEN** two workers launch from distinct projects in the same configured execution context
- **THEN** both use their own named profiles and the same prepared Hermes dependency environment
- **AND THEN** neither worker launch starts dependency installation, creates a private Python environment, or mutates the shared installation selection
- **AND THEN** a successful startup publishes the same managed identity for manager and gateway controls

#### Scenario: Prepared Installation Is Missing or Incompatible

- **WHEN** the configured installation is missing, stale, or lacks the required shared-profile, client, or caller-proof capabilities
- **THEN** Houmao fails preflight with the selected context and actionable preparation guidance
- **AND THEN** it leaves existing profiles, running workers, and project home links intact

#### Scenario: Worker Settings Require Unprepared Dependencies

- **WHEN** a worker's effective settings request a dependency unavailable in the prepared installation
- **THEN** launch refuses with owner-side preparation guidance before creating or replacing a worker binding

#### Scenario: Hermes Startup Fails

- **WHEN** qualified native startup fails for the selected mode or its native connection fails to initialize
- **THEN** Houmao reports the startup failure for that mode using the available diagnostics

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
