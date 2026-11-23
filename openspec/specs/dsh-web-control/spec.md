# dsh-web-control Specification

## Purpose

Define managed DeepSeek Harness interactive control through its Web Host, allowing a human browser and Houmao to share one live native agent session.

## Requirements

### Requirement: DSH Web Control Requires Houmao Launch Ownership

DSH Web control SHALL require a Web Host launched and owned by Houmao. Adoption of an externally launched host, including an otherwise compatible local host, SHALL be unsupported. Refusal SHALL leave that host unchanged. Reconnection or gateway attachment to an existing verified Houmao-owned host SHALL preserve its established binding without restarting the host or retargeting its session.

#### Scenario: Operator Tries to Adopt a Manually Started Host
- **WHEN** an operator requests adoption of a compatible local DSH Web Host started outside Houmao
- **THEN** the operation returns an explicit unsupported-capability response
- **AND THEN** it does not install companion assets, import credentials, mutate or restart the host, or take lifecycle ownership

#### Scenario: Gateway Reattaches to an Existing Owned Host
- **WHEN** a gateway or client reconnects to a verified live Web Host previously launched and owned by Houmao
- **THEN** it may resume control of the established managed binding after identity verification
- **AND THEN** it does not restart the host, retarget the native session, or replay earlier input

### Requirement: DSH Interactive Control Uses the Human Browser's Native Session

DSH interactive control SHALL address the same Web Host and native session used by the human browser. Programmatic prompts, observed history, progress, pending work, and terminal outcomes SHALL belong to that shared session. Browser navigation SHALL not silently change Houmao's bound target.

#### Scenario: Human and Program Alternate Prompts
- **WHEN** a human sends a prompt and Houmao later sends a prompt to the same bound DSH Web session
- **THEN** both interactions appear in that session's shared history and are observable by both clients
- **AND THEN** Houmao does not launch an ACP process or maintain a second conversation for interactive control

#### Scenario: Human Opens Another Browser Session
- **WHEN** the human switches the browser to another native conversation
- **THEN** Houmao continues addressing its explicitly bound native session

### Requirement: Web Control Is Bound to a Live Execution Incarnation

Managed Web operations SHALL identify the logical agent, runtime session, managed generation, Web Host incarnation, and native agent/session incarnation. Ordinary input SHALL require the expected live native target and SHALL not create or resume a cold session as a side effect. Explicit lifecycle operations SHALL remain separate from message delivery.

#### Scenario: Host Is Alive but the Native Agent Is Gone
- **WHEN** an ordinary message reaches a live host whose bound native agent has been disposed
- **THEN** delivery fails immediately with retryable unavailable or conflict semantics
- **AND THEN** the delivery does not activate a replacement agent

#### Scenario: A Session ID Is Reused After Restart
- **WHEN** a restarted host restores the same native session ID under a new incarnation
- **THEN** an attempt carrying the old incarnation is refused

### Requirement: Ordinary Web Admission Is Atomic at Native Handoff

Ordinary messages SHALL be admitted only while the expected native agent is live, idle, unblocked, and free of pending input under open gateway admission. The host SHALL recheck that state after asynchronous preparation and before input insertion without an intervening asynchronous boundary. Failed checks SHALL return immediately without storing the message for later delivery.

#### Scenario: Human Starts Work During Programmatic Preparation
- **WHEN** Houmao observes idle state but the human starts a turn before programmatic native handoff
- **THEN** the host refuses the ordinary programmatic attempt
- **AND THEN** it does not append the message to the native follow-up or steering inbox

#### Scenario: The Native Inbox Already Contains Input
- **WHEN** ordinary delivery reaches an idle or active session with pending input or uncertain pending-input state
- **THEN** the attempt is refused without waiting for the inbox to drain

### Requirement: Explicit Operator Policies Retain Distinct Meanings

Explicit Web prompt control SHALL preserve `ready_only`, `if_no_pending`, and `always` admission policies using native state. Only explicit operator policies permitting busy or pending input SHALL authorize native queueing. Ordinary plugin/message delivery SHALL always use ready-only admission and SHALL never be promoted to steering or forced queueing.

#### Scenario: Operator Explicitly Queues While Busy
- **WHEN** an operator selects `if_no_pending` for a live, unblocked busy Web agent with an empty native inbox
- **THEN** the input may enter the native next-turn queue under that explicit policy
- **AND THEN** an ordinary message in the same posture remains refused

#### Scenario: Forced Policy Does Not Override Availability
- **WHEN** an operator selects `always` for a dead, replaced, detached, or incompatible target
- **THEN** the request fails and creates no replacement execution or retained delivery

### Requirement: Native Admission and Shared Activity Are Separately Observable

Web prompt receipts SHALL identify native input admission without claiming completion. Managed results SHALL correlate native input identity and claimed turn evidence, while shared-session state SHALL include human and programmatic activity. A subsequent assistant message or session-idle transition alone SHALL not establish exclusive ownership by one caller.

#### Scenario: Human Steering Contributes to a Managed Turn
- **WHEN** a human steers an active turn that consumed a Houmao-submitted input
- **THEN** observation retains the turn's native identity and mixed-input evidence
- **AND THEN** the result does not claim that all output was caused exclusively by the programmatic prompt

#### Scenario: Admission Reply Is Lost
- **WHEN** native input was admitted but the client loses the admission response
- **THEN** the operation reports uncertainty and permits explicit read-only receipt reconciliation
- **AND THEN** transport recovery does not resubmit the input

### Requirement: Web Interruption Targets the Intended Live Activity

An operator interruption SHALL target the observed active native turn in the expected incarnation. Request-scoped cancellation SHALL affect only activity or pending input proven to belong to that attempt. Replacement or later unrelated activity SHALL remain untouched. Pending native work retained by cancellation SHALL remain visible in shared state.

#### Scenario: Operator Interrupts Human-Started Work
- **WHEN** an authorized operator explicitly interrupts the currently observed human-started native turn
- **THEN** the same shared session records the interruption and the browser observes it

#### Scenario: Late Request Cancellation Finds Another Turn
- **WHEN** a programmatic attempt has ended and its late cancellation reaches a newer human-started turn
- **THEN** the cancellation refuses the mismatched activity and does not interrupt that human turn

### Requirement: Web Failure Never Replays an Ordinary Message

Host or agent death, replacement, dispatch expiry, and connection loss SHALL produce explicit failure or uncertainty for affected pending operations. Reconnection SHALL be observational until the live binding is verified. Explicit restart/resume SHALL reconcile abandoned Houmao input before activation without discarding unrelated human input or replaying the failed delivery.

#### Scenario: Agent Dies After Native Admission
- **WHEN** a bound agent dies after accepting ordinary input but before a confirmed terminal result
- **THEN** the pending operation or recorded result reports failure or uncertainty
- **AND THEN** a later host, agent, gateway, or client restart does not automatically resend or reactivate that input

#### Scenario: Recovery Finds Both Human and Abandoned Program Input
- **WHEN** explicit recovery finds unclaimed human input and input identified as belonging to a failed Houmao attempt
- **THEN** it reconciles only the identified abandoned input through native operations
- **AND THEN** inability to establish safe reconciliation blocks activation instead of replaying the attempt

### Requirement: Browser and Program Use Independent Authorized Connections

The Web adapter SHALL authenticate its own connection and target only the managed local host/session. In `as_is` mode, the browser SHALL retain human question and approval participation by default. API credentials, launch tokens, signed URLs, and credential-bearing headers SHALL remain outside public manifests, status, diagnostics, and tracked evidence.

#### Scenario: Browser Answers While Houmao Observes
- **WHEN** the native agent requests human approval in `as_is` mode and the browser is connected
- **THEN** the human can answer while Houmao continues observing the same session
- **AND THEN** Houmao does not consume the question or silently approve it through its default API connection

#### Scenario: API Connection Credentials Expire
- **WHEN** the adapter's authenticated connection is revoked or closed
- **THEN** it reports unavailable control until an explicit verified reconnection succeeds
- **AND THEN** it does not replay earlier submitted input during reconnection

### Requirement: Web Lifecycle and Unsupported Controls Are Explicit

Managed launch, stop, and explicit relaunch SHALL supervise the owned Web Host while preserving native conversation and usage history according to the selected continuation mode. Capability inspection SHALL expose the browser surface and structured control support. Terminal capture, parser state, and raw-keystroke operations SHALL be explicitly unsupported for that surface.

#### Scenario: Raw Keystrokes Target a Web Agent
- **WHEN** a caller requests terminal keystrokes or a terminal-parser snapshot for DSH Web mode
- **THEN** the operation returns an unsupported-capability response without sending keys to the supervisor's log pane

#### Scenario: Operator Relaunches the Managed Web Host
- **WHEN** an operator explicitly relaunches the agent with exact native continuation
- **THEN** the same supported conversation is restored under a new execution incarnation
- **AND THEN** previous attempts keep their original outcomes and are not replayed

### Requirement: DSH Web Failures Surface Secret-Redacted Startup and Control Diagnostics

When a managed DSH Web Host fails during startup or returns an API control error during turn delivery, interruption, or relaunch, Houmao SHALL include a bounded, secret-redacted diagnostic summary from the supervisor exit record or Web API error payload in the surfaced failure detail. Launch tokens, session cookies, and resolved secret environment values SHALL remain excluded from surfaced diagnostics and public status payloads.

#### Scenario: Web Host Startup Failure Includes Sanitized Supervisor Reason
- **WHEN** a managed DSH Web Host exits before publishing verified bootstrap state and records a startup error
- **THEN** the launch failure includes a bounded, secret-redacted summary of the recorded startup failure rather than only a static generic message
- **AND THEN** launch tokens, cookies, and API keys are redacted if present

#### Scenario: Web Turn Control Failure Preserves Redacted Error Message
- **WHEN** the DSH Web control API returns a structured error during prompt admission, turn execution, interruption, or relaunch
- **THEN** Houmao surfaces both the error code and a bounded, secret-redacted error message in the resulting failure detail

### Requirement: An owned DSH Web host supports gateway browser sign-in

The DSH Web backend SHALL supply the owning gateway with a private native sign-in destination for its verified live host and managed session. The browser SHALL use DSH's native launch-token exchange to establish a separate cookie and open the managed session in its Workspace.

#### Scenario: A fresh browser enters through the gateway

- **WHEN** an operator redeems a valid ticket for a live DSH Web agent in a clean browser context
- **THEN** DSH establishes its native browser cookie and lands on a clean URL with the manifest-bound session selected in its Workspace
- **AND THEN** entry leaves the Workspace and session inventories unchanged, including when the target is blank

#### Scenario: Browser entry leaves the programmatic peer independent

- **WHEN** the browser signs in to the same host as Houmao's API peer
- **THEN** native browser authentication establishes a separate browser connection and preserves the managed API binding

#### Scenario: DSH bootstrap data does not match the live execution

- **WHEN** the credential source, native origin, authenticated host identity, or managed session membership fails its owner checks
- **THEN** the backend withholds the browser destination

#### Scenario: A fresh browser enters from an open gateway

- **WHEN** a clean browser opens the bare entry URL for a verified live DSH Web agent with a valid empty roster
- **THEN** the gateway immediately redirects to DSH's native browser sign-in destination
- **AND THEN** DSH establishes the browser's cookie and selects the managed session directly with the existing Workspace and session inventories

#### Scenario: A browser re-enters after navigating elsewhere

- **WHEN** an operator opens the gateway entry flow with a different native session saved in the browser
- **THEN** the new handoff selects the current managed session
- **AND THEN** subsequent native navigation and reload follow the browser's selection while Houmao prompts and mail notifications keep using the manifest-bound session

### Requirement: Managed DSH Web lifecycle verifies native Workspace membership

Houmao SHALL register or reuse the native Workspace for the canonical launch working directory. It SHALL verify that the Workspace includes the exact managed native session before publishing a ready DSH Web binding.

#### Scenario: A fresh session is available before its first turn

- **WHEN** Houmao launches DSH Web in a working directory with no native Workspace
- **THEN** one Workspace exists at that directory and its membership includes the manifest-bound native session before any prompt is submitted

#### Scenario: Exact relaunch retains the native session

- **WHEN** the operator explicitly relaunches DSH Web with the recorded exact session ID
- **THEN** the new execution publishes the same native session ID and verifies its membership in the same Workspace
- **AND THEN** repeated setup leaves one Workspace registration and one membership for that session

#### Scenario: An explicit replacement joins the managed Workspace

- **WHEN** the operator requests a new conversation through relaunch or an in-place reset
- **THEN** Houmao binds one replacement session in the same Workspace
- **AND THEN** prior and unrelated Workspace records, sessions, and histories are preserved

#### Scenario: Workspace setup fails

- **WHEN** the workdir or native membership cannot be verified during a managed lifecycle operation
- **THEN** Houmao reports a bounded, secret-redacted lifecycle error and withholds the ready binding for that execution
