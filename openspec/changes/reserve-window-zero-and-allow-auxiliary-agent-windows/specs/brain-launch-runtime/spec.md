## MODIFIED Requirements

### Requirement: Headless Claude/Gemini/Codex sessions are tmux-backed and inspectable
For headless sessions of tmux-backed CLI tools (at minimum Claude Code, Gemini, and Codex), the runtime SHALL create and own a tmux session per started session.

The runtime SHALL choose and persist one tmux session name per started session as a unique live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window `0` as the primary agent surface for that session and SHALL keep the headless agent itself on that primary surface across runtime-controlled turns.

The runtime SHALL name that stable primary window `agent`.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

The runtime SHALL allow auxiliary windows to exist later in the same tmux session for gateway, logs, or operator diagnostics, but they SHALL NOT displace the agent from window `0` and SHALL NOT redefine the primary headless attach surface.

Runtime-controlled headless turns SHALL continue targeting the pane in window `0` even when another tmux window is currently selected in the foreground for observability.

#### Scenario: Start a headless session creates a tmux identity with manifest pointer and primary agent window
- **WHEN** a developer starts a headless Codex, Claude, or Gemini session without CAO
- **THEN** the runtime creates a tmux-backed live session and persists its actual tmux session name as metadata for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH` pointing at the persisted session manifest JSON
- **AND THEN** window `0` is reserved as the primary agent surface for that session
- **AND THEN** that primary window is named `agent`

#### Scenario: Auxiliary windows do not replace the primary agent surface
- **WHEN** a tmux-backed headless session later creates another window for gateway, logs, or operator diagnostics
- **THEN** the headless agent remains anchored to window `0`
- **AND THEN** callers can continue treating window `0` as the canonical attach surface for that headless agent

#### Scenario: Foreground auxiliary window does not retarget headless execution
- **WHEN** a tmux-backed headless session has an auxiliary gateway or diagnostics window selected in the foreground
- **AND WHEN** the runtime starts another controlled headless turn
- **THEN** the controlled turn still executes on the agent surface in window `0`
- **AND THEN** the runtime does not need to reselect window `0` in the foreground to preserve that targeting contract

### Requirement: CAO session startup fixes "shell-first attach" and prunes the bootstrap window when safe
For CAO-backed session startup (`backend=cao_rest`), when the runtime pre-creates one bootstrap tmux window for env setup and CAO subsequently creates the real agent terminal window, the runtime SHALL normalize the tmux session so the CAO agent process occupies window `0`, SHALL best-effort make that CAO terminal window the session's current tmux window when startup completes, and SHALL prune the bootstrap window when it can be safely identified as distinct from the CAO terminal window.

The runtime SHALL record the bootstrap tmux `window_id` immediately after session creation and SHALL use `window_id` targeting, rather than index assumptions, for window selection, normalization, and pruning.

The runtime SHALL resolve the CAO terminal window id from `terminal.name` using bounded retry to tolerate transient tmux visibility races. If the CAO window cannot be resolved within the bound, startup SHALL still succeed and the runtime SHALL emit a warning diagnostic.

The runtime SHALL use the `create_terminal(...)` response `terminal.name` as the CAO tmux window name and SHALL NOT issue an extra `GET /terminals/{id}` solely to obtain that name.

When the bootstrap window and the resolved CAO terminal window are distinct, the runtime SHALL first prune the recorded bootstrap window and SHALL then move the resolved CAO terminal window into tmux window `0` before treating same-session auxiliary-window topology as available for that session.

When the runtime cannot safely determine how to preserve the CAO terminal as the canonical agent surface during normalization, or when prune or move cannot safely establish the CAO terminal in tmux window `0`, it SHALL refuse same-session auxiliary-window topology for that session rather than guessing.

#### Scenario: Successful CAO startup leaves the agent terminal in window 0
- **WHEN** a developer starts a CAO-backed session and terminal creation succeeds
- **AND WHEN** the runtime can resolve the CAO terminal window safely
- **THEN** the runtime normalizes that CAO terminal to tmux window `0`
- **AND THEN** the tmux session remains active with the CAO terminal as the canonical agent surface

#### Scenario: Successful CAO startup prunes a distinct bootstrap window
- **WHEN** a developer starts a CAO-backed session and terminal creation succeeds
- **AND WHEN** the recorded bootstrap window differs from the resolved CAO terminal window
- **THEN** the runtime removes the recorded bootstrap window from that tmux session
- **AND THEN** the runtime moves the resolved CAO terminal window into tmux window `0`
- **AND THEN** the runtime selects the CAO terminal window as the session's current window
- **AND THEN** the CAO terminal remains the canonical agent surface in window `0`

#### Scenario: Runtime skips prune when bootstrap and terminal window are the same
- **WHEN** the recorded bootstrap window resolves to the same tmux window as the CAO terminal
- **THEN** the runtime skips bootstrap-window deletion
- **AND THEN** the CAO terminal remains active as the canonical agent surface in window `0` for subsequent prompt or stop operations

#### Scenario: Runtime refuses same-session auxiliary windows when CAO surface normalization is unsafe
- **WHEN** a CAO-backed session cannot safely determine or preserve the live CAO terminal as the canonical agent surface in window `0`
- **THEN** the runtime does not create a same-session auxiliary gateway or monitoring window for that session
- **AND THEN** the runtime preserves the existing CAO session without guessing at a replacement agent surface

## ADDED Requirements

### Requirement: Supported runtime-managed tmux sessions keep the agent in window 0 while auxiliary windows remain non-authoritative
For runtime-managed tmux sessions that place gateway, monitoring, or other support processes in the same tmux session, the runtime SHALL reserve tmux window `0` for the agent process.

The runtime SHALL support that same-session auxiliary-window topology for tmux-backed headless backends and for `cao_rest`.

The runtime SHALL NOT apply that same-session auxiliary-window topology to `houmao_server_rest`, whose control services remain out of the agent's tmux session.

Only tmux window `0` is contractual in that topology. The names, counts, and indices of non-zero tmux windows SHALL remain implementation details and SHALL NOT become part of the public attach or control contract.

For headless sessions, the stable public window name for window `0` SHALL remain `agent`.

For `cao_rest`, the runtime SHALL preserve CAO terminal identity semantics where possible while still keeping the agent process in window `0`.

Gateway attach, detach, crash cleanup, or auxiliary-window recreation SHALL NOT kill, replace, or repurpose the reserved agent window `0` during normal lifecycle handling.

If the agent process later disappears unexpectedly and the runtime relaunches it inside the same tmux session, the runtime SHALL restore the agent process to window `0` before treating the session as recovered or ready again.

#### Scenario: Headless auxiliary window keeps the agent anchored to window 0
- **WHEN** a tmux-backed headless session runs a gateway or monitoring process in another tmux window
- **THEN** the agent process remains in window `0`
- **AND THEN** the non-zero process window does not become part of the public agent contract

#### Scenario: CAO auxiliary window keeps the CAO terminal anchored to window 0
- **WHEN** a `cao_rest` session runs a gateway or monitoring process in another tmux window
- **THEN** the CAO agent process remains in window `0`
- **AND THEN** the non-zero process window does not become part of the public agent contract

#### Scenario: Houmao-server sessions keep control services out of the agent tmux session
- **WHEN** a developer starts or resumes a `houmao_server_rest` session with gateway capability
- **THEN** control services remain outside the agent's tmux session
- **AND THEN** the runtime does not create a same-session gateway or monitoring window for that server-backed session

#### Scenario: Gateway lifecycle preserves the reserved agent window
- **WHEN** a same-session gateway or monitoring process attaches, detaches, exits unexpectedly, or is recreated
- **THEN** the runtime only changes the auxiliary process window state
- **AND THEN** window `0` remains reserved for the agent surface throughout that sidecar lifecycle

#### Scenario: Relaunch restores the agent process to window 0
- **WHEN** an agent process in a supported same-session tmux layout disappears unexpectedly and the runtime relaunches it in the existing tmux session
- **THEN** the runtime restores the relaunched agent process to window `0`
- **AND THEN** the session is not treated as recovered until that canonical agent surface is re-established
