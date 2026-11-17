# Spec Delta

## ADDED Requirements

### Requirement: DSH TUI Posture Resolves to a Web Backend

Selecting DSH through Houmao's existing `tui` or non-headless interactive posture SHALL resolve to backend `dsh_web`. Its human interface SHALL be the native DSH Web application, and semantic control SHALL use the same host/session's Web API. Explicit headless selection SHALL continue resolving to `dsh_acp`.

#### Scenario: Developer Launches DSH Interactively
- **WHEN** a valid DSH definition or profile is launched through the maintained interactive manager path
- **THEN** Houmao starts its managed Web Host and returns its bound native session and browser-surface metadata
- **AND THEN** the developer does not need a new DSH-specific interaction-mode flag

#### Scenario: A DSH Headless Profile Is Launched
- **WHEN** the selected DSH launch posture is headless
- **THEN** it retains the qualified ACP behavior from change 01 without starting a Web listener

### Requirement: Native Human Surface Is Distinct From Process Supervision

Interactive runtime and discovery metadata SHALL distinguish terminal and Web native surfaces. A Web surface SHALL expose a non-secret browser location and native session identity. Optional tmux supervision SHALL describe host logs and lifecycle only; its existence SHALL not imply a terminal agent interface, key control, or parser support.

#### Scenario: A Web Host Is Supervised in Tmux
- **WHEN** the DSH Web process runs under a managed tmux supervisor
- **THEN** agent inspection identifies the browser as the native human surface
- **AND THEN** terminal observers do not parse the supervisor's log pane as a DSH TUI

#### Scenario: Native Surface Metadata Is Incompatible
- **WHEN** a persisted DSH Web record claims a terminal parser or lacks a verifiable host/session binding
- **THEN** runtime validation reports the incompatible record rather than guessing readiness from tmux liveness

### Requirement: Managed DSH Web Startup Publishes Only Verified Authority

DSH Web startup SHALL use the isolated configuration and native prompt projection established for DSH. Before publishing ready control, Houmao SHALL verify the owned local host, required companion protocol/build, bound native session, and execution incarnations. Startup failure SHALL roll back the newly owned process and partial discovery state without changing another host.

#### Scenario: The Host Starts Without Its Managed Control Companion
- **WHEN** the DSH HTTP listener starts but the required companion is absent or incompatible
- **THEN** launch fails without publishing a controllable managed agent
- **AND THEN** the newly owned host is stopped

#### Scenario: Two DSH Web Agents Share a Project
- **WHEN** two DSH Web agents are launched in the same project
- **THEN** their homes, listeners, native session bindings, connection credentials, and execution authority remain isolated

### Requirement: Web Human Interaction Follows the Selected Operator Policy

DSH Web launch SHALL preserve native human questions, permissions, and model selection in `as_is` mode. Unattended mode SHALL apply its separately qualified no-question policy without silently approving native hard denies. Opening the browser SHALL be explicit, and credentials required for browser sign-in SHALL not enter ordinary public launch/status metadata.

#### Scenario: Human Operates an As-Is DSH Session
- **WHEN** an interactive DSH agent uses `as_is` mode and requests approval
- **THEN** the browser presents the native interaction while Houmao observes its blocked state
- **AND THEN** the Web adapter does not apply unattended policy on resume or status inspection

#### Scenario: Automated Web Qualification Has No Display
- **WHEN** an unattended DSH Web fixture launches on a host without a desktop browser
- **THEN** the host becomes controllable without automatically opening a graphical application
- **AND THEN** browser qualification can connect separately to the same bound native session

### Requirement: Web Relaunch Preserves Logical Identity and Changes Execution Identity

Explicit DSH Web relaunch SHALL preserve the logical agent and runtime-session history while establishing a new host/agent incarnation. Exact continuation SHALL restore only the selected supported conversation after failed-input reconciliation. Read-only control reconstruction SHALL never relaunch the host, replay work, or overwrite newer persisted native state.

#### Scenario: A Stale Controller Inspects a Relaunched Host
- **WHEN** a separately held controller inspects status or attaches a gateway after explicit Web relaunch
- **THEN** it observes the current persisted host/session incarnation
- **AND THEN** it does not restore the old endpoint, native conversation, or execution token

#### Scenario: A Gateway Restarts While the Web Host Stays Live
- **WHEN** gateway control reconnects to an unchanged verified Web Host and bound session
- **THEN** observation resumes without restarting the DSH agent or changing its conversation
