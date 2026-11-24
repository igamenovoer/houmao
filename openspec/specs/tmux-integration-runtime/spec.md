## Purpose
Define the repo-owned tmux integration boundary for libtmux-backed discovery, explicit surface resolution, and bounded fallback command usage.
## Requirements
### Requirement: Repo-owned tmux integration is libtmux-first
The repository SHALL use one shared libtmux-backed integration layer for Python tmux discovery, lookup, capture, control, and lifecycle operations. The layer SHALL use libtmux's object API when it preserves the operation's contract and libtmux command dispatch for missing fields, flags, or checked results. Direct tmux processes SHALL be limited to documented cases that require process behavior libtmux cannot provide.

#### Scenario: Acceptance criteria

- **GIVEN** a repo-owned Python flow performs a tmux operation
- **THEN** the shared integration layer binds the operation to the selected tmux server
- **AND THEN** a direct tmux process is used only for a documented capability gap

#### Scenario: Session lookup uses libtmux objects
- **WHEN** repo-owned runtime code needs to resolve a live tmux session and enumerate its panes
- **THEN** it uses the shared libtmux-backed integration layer
- **AND THEN** the layer uses checked libtmux command dispatch if the object API loses information needed to verify the result

#### Scenario: Missing high-level field falls back through libtmux command dispatch
- **WHEN** repo-owned code needs tmux data such as a format field that libtmux does not expose directly as a first-class property
- **THEN** it issues the fallback query through libtmux-owned command dispatch bound to the relevant server, session, window, or pane object

#### Scenario: Prompt buffer load requires process stdin
- **WHEN** the runtime loads a prompt as tmux buffer data from standard input
- **THEN** the shared layer can invoke the native buffer loader on the selected server
- **AND THEN** the prompt text is carried through standard input and stays out of command arguments

### Requirement: Session-scoped pane enumeration spans the full session
When a repo-owned tmux-facing flow asks for panes in a tmux session, that enumeration SHALL span all panes in the addressed session, including panes in non-current windows.

The system SHALL NOT treat a bare session target as permission to inspect only the current tmux window when the workflow contract is session-scoped pane discovery.

#### Scenario: Auxiliary pane in a non-current window remains discoverable
- **WHEN** tmux session `S` has current window `0` and another live pane in auxiliary window `1`
- **THEN** a session-scoped pane enumeration for `S` returns panes from both windows
- **AND THEN** the pane in window `1` is not hidden merely because window `0` is current

### Requirement: Explicit tmux surface identity outranks current-focus heuristics
When a repo-owned tmux-facing flow must observe or control a specific tmux surface, it SHALL resolve that surface from explicit pane or window identity before considering current active-window or active-pane state.

Current-focus heuristics MAY be used only when the workflow contract explicitly means the current operator focus or when the session has exactly one unambiguous candidate pane.

#### Scenario: Stored window identity wins over current focus
- **WHEN** a tmux-backed workflow stores the contractual target as pane `%1` or window `1`
- **AND WHEN** another window in the same session becomes current
- **THEN** the workflow continues observing or controlling the stored target surface
- **AND THEN** it does not silently rebind to the current active window

#### Scenario: Ambiguous multi-pane session does not guess from current focus
- **WHEN** a tmux-backed workflow needs one specific surface in a session that has multiple candidate panes
- **AND WHEN** the workflow has no explicit pane or window identity for that contract
- **THEN** the workflow fails explicitly or remains in a non-authoritative diagnostic posture
- **AND THEN** it does not silently guess from the current active pane

### Requirement: Operator-facing tmux handoff is interactivity-aware and libtmux-backed
When repo-owned Houmao code needs to hand an operator terminal off to a tmux session after a successful managed launch, it SHALL resolve the session through the repo-owned libtmux-backed tmux integration layer rather than composing an ad hoc raw `tmux attach-session` subprocess call.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

If libtmux does not expose a first-class attach helper for the needed session handoff, the implementation SHALL use libtmux-owned command dispatch bound to the resolved tmux server or session object rather than introducing a separate unrelated raw tmux subprocess path.

Before attempting tmux attach, the handoff flow SHALL determine whether the caller provides a usable interactive terminal. When the caller is non-interactive, the handoff flow SHALL skip the attach attempt and return or report tmux session coordinates for manual follow-up instead of surfacing raw tmux `not a terminal` output as a launch failure.

#### Scenario: Interactive caller uses libtmux-backed session handoff
- **WHEN** a repo-owned managed launch flow needs to attach an interactive caller to tmux session `S`
- **AND WHEN** the caller provides a usable interactive terminal
- **THEN** the flow resolves session `S` through the repo-owned libtmux integration layer
- **AND THEN** any resulting attach command is issued through libtmux-owned command dispatch rather than through an unrelated raw tmux subprocess helper

#### Scenario: Non-interactive caller skips attach and reports follow-up coordinates
- **WHEN** a repo-owned managed launch flow finishes starting tmux session `S`
- **AND WHEN** the caller does not provide a usable interactive terminal
- **THEN** the flow does not attempt a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** it reports the tmux session coordinates needed for a later manual attach

### Requirement: Primary managed-agent surface keeps window zero contract and persists tmux object handles
The runtime SHALL treat window index `0` as the primary window of a Houmao-owned managed-agent session. The session manifest's `tmux` section SHALL provide the authoritative socket, session, and primary window and pane handles. Serialized copies of those coordinates SHALL be derived from that binding.

#### Scenario: Acceptance criteria

- **GIVEN** a valid binding to the managed primary pane or window
- **THEN** runtime control, capture, prompt submission, interruption, and health checks target that pane or window by its tmux id

#### Scenario: Fresh launch under one-based tmux defaults records primary handles
- **WHEN** tmux is configured so a newly created session starts with window index `1` and pane index `1`
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** the runtime establishes the managed-agent primary window at index `0`
- **AND THEN** it records the owner socket and session with the live primary window and pane ids for later operations

#### Scenario: Runtime operation targets the persisted pane id
- **WHEN** a managed-agent manifest contains primary pane id `%7` for tmux session `HOUMAO-worker`
- **AND WHEN** Houmao sends prompt text, capture requests, or interrupt control to the primary managed-agent surface
- **THEN** the tmux operation targets `%7` on the manifest's socket
- **AND THEN** the operation does not depend on reconstructing `HOUMAO-worker:0.0`

#### Scenario: The manifest binds the operation to one server
- **WHEN** two tmux servers have sessions with the same name and overlapping window and pane ids
- **AND WHEN** the caller runs inside the server that does not own the managed agent
- **THEN** the runtime observes and addresses only the manifest's server for that agent

#### Scenario: Publishing terminal coordinates uses one binding
- **WHEN** the runtime writes a managed manifest or publishes registry terminal coordinates
- **THEN** the corresponding provider and registry projections use the same authoritative binding

### Requirement: Primary tmux handles are validated against the window zero authority before use
The runtime SHALL validate saved primary handles against a checked observation of the owning socket, session, and window `0`. Read-only observations SHALL leave saved bindings unchanged. An owner-authorized operation MAY repair absent or stale handles before continuing, provided the replacement pane is unique and actionable and the expected binding and generation are still current.

#### Scenario: Acceptance criteria

- **GIVEN** the primary window authority is absent or ambiguous or has no actionable primary pane
- **THEN** the requested primary-pane operation fails explicitly and leaves the saved binding unchanged

#### Scenario: Stale pane id is refreshed from primary window zero
- **WHEN** a managed-agent manifest contains stale primary pane id `%7`
- **AND WHEN** the owner requests a control operation that allows repair and observes a single actionable managed-agent pane in window index `0`
- **THEN** the runtime refreshes the saved primary window and pane ids together
- **AND THEN** the requested operation continues against the refreshed pane id

#### Scenario: Missing primary window fails closed
- **WHEN** a managed-agent manifest references tmux session `HOUMAO-worker`
- **AND WHEN** the tmux session exists but has no window index `0`
- **THEN** the runtime reports degraded or stale primary tmux authority
- **AND THEN** it does not choose another window only because that window is current or active

#### Scenario: Read-only inspection reports a stale binding
- **WHEN** a read-only operation observes a replacement pane in the primary window
- **THEN** it can report the observed pane and the stale saved binding
- **AND THEN** the manifest and registry are unchanged

#### Scenario: A newer generation or binding wins a repair race
- **WHEN** an owner-authorized repair has observed a replacement pane
- **AND WHEN** the manifest generation or primary binding changes before the repair is committed
- **THEN** the repair based on the old observation cannot overwrite the current binding or act through the proposed replacement pane

### Requirement: Houmao-launched tmux sessions inject interactive terminal defaults
Houmao-created tmux sessions SHALL apply a Houmao-owned configuration overlay by default after tmux has loaded the user's normal configuration.

The overlay SHALL enable mouse mode for the launched session and SHALL configure rich color support for the launched tmux surface.

The overlay SHALL only set the tmux options and session environment values Houmao explicitly owns for this behavior, and SHALL leave unrelated user tmux configuration values unchanged.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The overlay SHALL be disabled when `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` is present in the launching environment.

#### Scenario: Launched session receives mouse and rich-color defaults
- **WHEN** Houmao creates a tmux-backed managed-agent session
- **AND WHEN** `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is unset
- **THEN** Houmao applies its tmux configuration overlay after creating the session
- **AND THEN** the launched session has mouse mode enabled
- **AND THEN** the launched session advertises a 256-color tmux terminal with true-color capability for provider processes

#### Scenario: User configuration remains otherwise intact
- **WHEN** the user's tmux configuration defines options unrelated to Houmao's mouse and rich-color overlay
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** Houmao does not clear or rewrite those unrelated tmux options
- **AND THEN** only the Houmao-owned mouse, terminal identity, true-color, and color environment values are overlaid

#### Scenario: Environment opt-out disables injection
- **WHEN** the launching environment contains `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** Houmao does not apply its tmux configuration overlay
- **AND THEN** Houmao preserves the existing launch environment color behavior instead of forcing rich-color defaults

### Requirement: Houmao launch environment removes inherited color suppression when injection is enabled

When tmux configuration injection is enabled, Houmao SHALL publish terminal color environment values into launched tmux sessions that support rich color output.

The published environment SHALL set `TERM=tmux-256color`, set `COLORTERM=truecolor`, and prevent inherited `NO_COLOR` from suppressing color in managed provider processes.

The color overlay SHALL preserve unrelated environment values admitted by the launch environment contract.

#### Scenario: Inherited NO_COLOR does not suppress managed session color
- **WHEN** the launching process has `NO_COLOR=1`
- **AND WHEN** `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is unset
- **AND WHEN** Houmao launches a tmux-backed managed-agent session
- **THEN** the launched provider environment does not contain `NO_COLOR`
- **AND THEN** the launched provider environment contains `TERM=tmux-256color`
- **AND THEN** the launched provider environment contains `COLORTERM=truecolor`

#### Scenario: Unrelated environment values are preserved
- **WHEN** the resolved launch environment contains a declared `FEATURE_FLAG_X=enabled`
- **AND WHEN** Houmao launches a tmux-backed managed-agent session with tmux configuration injection enabled
- **THEN** the launched provider environment still contains `FEATURE_FLAG_X=enabled`
- **AND THEN** Houmao only changes the color-related environment variables it owns for the injection behavior

### Requirement: Tmux configuration injection failures guide operator recovery
If Houmao creates a tmux session but cannot apply the enabled tmux configuration injection, the launch SHALL fail with an error that identifies tmux configuration injection as the failing step.

The error SHALL include guidance that the operator can retry with `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` to disable the overlay.

When practical, Houmao SHALL clean up the newly-created tmux session before returning the launch failure.

#### Scenario: Injection failure reports opt-out guidance
- **WHEN** Houmao creates tmux session `S`
- **AND WHEN** the tmux configuration injection command fails
- **THEN** the launch fails with an error that names tmux configuration injection
- **AND THEN** the error includes `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` as the disablement mechanism
- **AND THEN** Houmao attempts to remove tmux session `S`

### Requirement: Tmux-backed provider processes inherit launch-profile env records

For Houmao-started tmux-backed agents, the owning session SHALL contain the resolved publishable launch values before the provider starts. Headless, Service, TUI, and Web SHALL receive those same values in the provider environment. Failure to publish a required value SHALL prevent that provider start.

#### Scenario: Profile proxy env is visible to provider process
- **WHEN** a launch plan for a local interactive Codex session contains launch-profile-derived env records `http_proxy=http://127.0.0.1:7990`, `https_proxy=http://127.0.0.1:7990`, and `FEATURE_FLAG_X=profile-env`
- **AND WHEN** Houmao creates the tmux-backed managed-agent session and starts the Codex TUI process in the primary pane
- **THEN** the provider process inherits `http_proxy=http://127.0.0.1:7990`
- **AND THEN** the provider process inherits `https_proxy=http://127.0.0.1:7990`
- **AND THEN** the provider process inherits `FEATURE_FLAG_X=profile-env`

#### Scenario: Tmux session environment contains profile env before provider startup
- **WHEN** Houmao prepares a tmux-backed managed-agent session for a launch plan containing launch-profile env records
- **THEN** the tmux session environment contains those launch-profile env records before the local interactive provider command is started
- **AND THEN** unrelated Houmao-owned tmux configuration injection does not remove those launch-profile env records

#### Scenario: A Web host or service supervisor starts after environment publication
- **WHEN** Houmao starts a Web or Service agent with non-secret root selectors, persistent settings, and one-off settings
- **THEN** the owning tmux session contains those values before the supervisor starts the native provider
- **AND THEN** the provider environment contains the same values

#### Scenario: A required session environment value cannot be set
- **WHEN** publication of a required launch value in the owning tmux session fails
- **THEN** the provider does not start for that generation
- **AND THEN** the error identifies the publication step and the affected name without printing the value

### Requirement: Owned tmux session launch values exclude credentials

The runtime SHALL write only publishable launch values to the owned tmux session. It SHALL prevent credential values from entering the session through Houmao-controlled tmux server startup or session inheritance.

#### Scenario: A credential is present in the launching environment

- **WHEN** a managed launch uses a provider credential that is also present in the owner environment
- **THEN** the credential value is absent from the owned tmux session environment and its pane command
- **AND THEN** a session launched on a fresh tmux server does not seed the server environment with that credential

#### Scenario: An existing server carries a credential name

- **WHEN** an existing tmux server has a selected credential name in its global environment
- **THEN** the owned session masks the inherited credential for its panes
- **AND THEN** the selected provider receives the value through its private launch input

### Requirement: Relaunch reconciles the owned tmux launch environment

Before a new managed generation starts, the runtime SHALL replace its published session values with the new effective values and mask expired managed keys from tmux inheritance. Writes SHALL target the owned session and preserve unrelated user-managed tmux values.

#### Scenario: A one-off setting expires while the server defines the same name

- **WHEN** the old generation published a one-off setting and the next generation does not use that key
- **AND WHEN** the tmux server has a global value for the same key
- **THEN** the relaunched session omits the old setting and panes started in that session do not inherit the global value
- **AND THEN** unrelated session settings are preserved

### Requirement: Tmux failures remain distinguishable from target absence
The shared runtime SHALL report target absence only when the result confirms it. Socket access failures, command failures without conclusive evidence, and invalid observations SHALL remain distinguishable from absence. A failed observation SHALL prevent implicit repair or retargeting.

#### Scenario: An inaccessible socket gives no evidence that the target is missing
- **WHEN** a query against the owning socket fails without confirming target absence, including a nonzero exit with empty output
- **THEN** the runtime reports a failed observation and retains the saved binding

#### Scenario: A checked observation confirms an absent target
- **WHEN** a successful observation of the relevant session or server confirms the requested target is absent
- **THEN** the runtime reports the target as missing

#### Scenario: A checked mutation fails without stderr
- **WHEN** a tmux mutation returns a nonzero status with empty stderr
- **THEN** the runtime reports the mutation failure and does not treat it as successful or replay it against another target

### Requirement: A selected tmux server has an explicit startup policy

`user-default` SHALL select the execution account’s native default independently of the enclosing tmux session. `new` SHALL allocate a fresh owner-private socket for each new instance. Both modes and `houmao-default` SHALL allow startup at their selected address. `socket` SHALL require an existing server for session creation. Each launch SHALL target its resolved address exclusively.

#### Scenario: The native default is selected from another server

- **WHEN** an execution account inside tmux on a non-default socket launches with `user-default`
- **THEN** the launch uses the account’s native default socket and starts that server if needed

#### Scenario: Two fresh births request a private server

- **WHEN** two new instances launch with `new`
- **THEN** they start successfully on distinct owner-private sockets even if their session names are identical

#### Scenario: The specified server exits after preflight

- **WHEN** an existing-only server disappears between preflight and session creation
- **THEN** launch returns an error for the specified socket without starting a server or connecting elsewhere

### Requirement: Relaunch preserves the concrete socket and startup permission

Tmux-backed managed birth SHALL persist the resolved socket and startup permission with the runtime binding. Later tmux operations SHALL use the persisted socket. Relaunch SHALL apply the saved startup permission at that address even when the original profile or default record has changed.

#### Scenario: Relaunch reuses a private socket after profile edit

- **GIVEN** a stopped instance born with `new` whose server has exited
- **WHEN** an operator relaunches the instance after editing the profile
- **THEN** the runtime starts the session at the socket saved in the manifest

#### Scenario: Relaunch preserves the existing-only contract

- **GIVEN** an instance that originally selected `socket`
- **WHEN** an operator relaunches it while its recorded server is unavailable
- **THEN** relaunch reports the unavailable server without starting or selecting another one
