# Spec Delta

## Purpose

Define how Houmao builds, launches, controls, and observes managed Hermes agents in terminal, persistent service, and finite CLI modes.

## ADDED Requirements

### Requirement: Managed Hermes Launch Resolves the Command on PATH

Houmao SHALL determine Hermes executable availability solely with `command -v hermes` in the selected execution context. A successful lookup SHALL allow launch of the requested supported mode using the resolved command. A failed lookup SHALL report that Hermes is missing from PATH before changing the managed home or existing runtime.

#### Scenario: Hermes Is on PATH

- **WHEN** an operator selects a supported Hermes mode and `command -v hermes` succeeds in the selected execution context
- **THEN** Houmao attempts startup with the resolved command and its selected backend
- **AND THEN** a successful startup publishes the same managed identity for manager and gateway controls

#### Scenario: Hermes Is Missing From PATH

- **WHEN** the selected execution context cannot find `hermes` on PATH
- **THEN** Houmao reports the missing command and identifies the context where PATH must be corrected
- **AND THEN** the managed home and any existing runtime remain intact

#### Scenario: Hermes Startup Fails

- **WHEN** the resolved command fails to start the selected mode or its native connection fails to initialize
- **THEN** Houmao reports the startup failure for that mode using the available diagnostics

### Requirement: Hermes State and Configuration Belong to the Managed Agent

Houmao SHALL bind the selected agent to an isolated Hermes home, gateway rendezvous scope, and explicit workspace. It SHALL project its role, selected skills, tool policy, model route, and privately referenced credentials into native configuration while keeping its existing managed identity.

#### Scenario: Two Agents Have Separate Homes

- **WHEN** two Hermes agents launch under one OS user
- **THEN** each binds a separate home, daemon, session store, workspace, and selected configuration and credential source
- **AND THEN** their runtime inputs and histories remain separately addressable

#### Scenario: A Managed Role and Skill Pack Are Selected

- **WHEN** an operator launches a managed agent from a profile with a role and managed skills
- **THEN** Hermes reads the effective role through its native identity input and discovers the selected skills through its own skill loader
- **AND THEN** Houmao's self-identity and gateway access reach the owned execution context

#### Scenario: Browser and Desktop Control Are Excluded

- **WHEN** the managed Hermes launch uses its default tool posture
- **THEN** it exposes the qualified toolsets with browser and desktop-control tools excluded
- **AND THEN** startup and prompts do not acquire those optional binaries on demand

### Requirement: Hermes Lifecycle Verifies the Owned Native Authority

Houmao SHALL bind managed execution to its recorded Hermes home and selected logical session. It SHALL record the daemon incarnation and runtime generation for lifecycle operations and turn evidence. Gateway detach or client loss SHALL preserve accepted work. After a daemon replacement, Houmao SHALL reconcile existing work using attributable evidence before reopening admission.

#### Scenario: Houmao Gateway Reattaches During an Accepted Turn

- **WHEN** the Houmao gateway restarts while its Hermes daemon remains available
- **THEN** the gateway recovers status through the same managed owner and does not dispatch another prompt
- **AND THEN** a terminal event from another session, authority incarnation, or admission cannot settle the original request

#### Scenario: Hermes Restarts After Admission

- **WHEN** the owned Hermes daemon exits after accepting managed work
- **THEN** Houmao preserves the recorded admission and the distinction between queued and started work
- **AND THEN** any native recovery of a persisted queue entry is observed as the original admission
- **AND THEN** unresolved execution stays uncertain without a fresh managed submission

#### Scenario: Exact Relaunch Has No Matching Session

- **WHEN** the manager verifies a requested saved logical session before launch and finds that it is missing or belongs to another home or workspace
- **THEN** the manager refuses exact continuation before submission
- **AND THEN** it does not move the workspace, select a recent conversation, or create a replacement conversation

#### Scenario: Operator Stops One of Two Managed Hermes Agents

- **WHEN** stop targets one Hermes agent whose daemon was started or adopted by Houmao
- **THEN** Houmao verifies the targeted process identities, stops those processes, and preserves the record needed for explicit relaunch
- **AND THEN** another agent's daemon, conversation, and terminal remain available

### Requirement: Hermes Daemon Ownership Follows the Managed Launch Home

Houmao SHALL manage the daemon launched for the exact standalone Hermes home it created and recorded. It SHALL start a daemon when needed and adopt any existing daemon launched for that home without seeking consent or notifying its starter. Independent use of the managed home has undefined behavior.

#### Scenario: The Managed Home Has No Daemon

- **WHEN** Houmao needs native execution and the managed home has no daemon
- **THEN** Houmao starts one directly or through the native client's local startup and records its verified process identity

#### Scenario: A Daemon Is Already Running in the Managed Home

- **WHEN** Houmao finds a daemon whose launch home matches the recorded managed home, including one a user or native client started
- **THEN** Houmao adopts its verified process identity regardless of its starter
- **AND THEN** normal readiness still requires the protocol capabilities used by the selected mode

#### Scenario: A Native Client Starts a Same-Home Replacement

- **WHEN** a daemon exits during client attachment and native local startup brings up a replacement for the same managed home
- **THEN** Houmao adopts the replacement and records its process identity
- **AND THEN** previously admitted requests retain their original evidence and reconcile before new work is accepted

#### Scenario: A Discovered Daemon Has a Different Launch Home

- **WHEN** discovery finds a gateway launched for a different home, even if it serves the managed home as a secondary profile
- **THEN** Houmao leaves that daemon outside managed control and reports native availability only after verifying a connection to a daemon launched for the recorded home

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

Hermes service mode SHALL own a persistent `hermes acp` client and its verified Hermes daemon. The adapter SHALL negotiate the protocol and bind the exact logical session before publishing readiness. It SHALL correlate prompt settlement, reverse interactions, and cancellation to the current operation.

#### Scenario: Two Prompts Use the Same ACP Service

- **WHEN** consecutive requests are admitted to the same healthy service
- **THEN** both use the same ACP process, daemon, and bound session
- **AND THEN** resume-time replay remains historical evidence

#### Scenario: ACP Requests an Approval

- **WHEN** the peer asks for a tool approval during a turn
- **THEN** the owner responds using the authorized native policy and an advertised option while it continues to drain protocol output
- **AND THEN** unqualified client facilities or unanswered user interactions do not silently grant access

#### Scenario: ACP Disconnects During Work

- **WHEN** the ACP process or stream disappears after a prompt may have been submitted
- **THEN** the owner reports uncertainty until it verifies the exact native outcome
- **AND THEN** viewer exit is insufficient evidence of cancellation

### Requirement: Hermes Headless Uses a Finite Structured CLI Client

Every accepted Hermes headless turn SHALL use one finite `hermes chat` CLI client with literal input and structured JSONL output. Houmao SHALL verify the logical session ID and workspace before continuation and pass that ID unchanged to stock `--resume`, which uses Hermes's native lookup behavior. Houmao SHALL retain raw turn artifacts and publish attributable semantic events separately.

#### Scenario: Two Headless Prompts Continue the Same Session

- **WHEN** the second prompt explicitly continues the first native conversation and Hermes resolves the verified ID
- **THEN** Houmao starts a new CLI process with `--resume <full-id>` in the verified workspace
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
