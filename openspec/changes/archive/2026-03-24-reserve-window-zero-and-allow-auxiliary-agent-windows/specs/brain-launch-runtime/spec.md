## MODIFIED Requirements

### Requirement: Pair-managed `houmao_server_rest` sessions are tmux-backed, reserve window 0, and publish stable gateway attachability before live attach
For pair-managed TUI sessions that use `backend = "houmao_server_rest"`, the runtime SHALL create or resume one tmux session per managed agent session.

The runtime SHALL choose and persist one tmux session name per launched session as a stable live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window `0` as the primary agent surface for that session and SHALL keep the managed agent itself on that primary surface across pair-managed turns.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that pair-managed discovery can locate the persisted session manifest.

The runtime SHALL reuse the existing runtime-owned gateway capability publication seam to materialize `gateway/attach.json`, `gateway/state.json`, queue/bootstrap assets, and the stable gateway attachability pointers `AGENTSYS_GATEWAY_ATTACH_PATH=<absolute attach path>` and `AGENTSYS_GATEWAY_ROOT=<absolute gateway root>` during pair launch or launch registration, before a live gateway is attached.

A pair-managed session SHALL NOT be treated as current-session attach-ready until both that runtime-owned gateway capability publication and successful managed-agent registration for the same persisted `api_base_url` and `session_name` have completed.

The runtime SHALL allow auxiliary windows to exist later in the same tmux session for gateway or operator diagnostics, but they SHALL NOT displace the agent from window `0` and SHALL NOT redefine the primary pair-managed attach surface.

Runtime-controlled pair-managed turns and pair-managed tmux resolution SHALL continue targeting the agent surface in window `0` even when another tmux window is currently selected in the foreground for observability.

#### Scenario: Pair launch creates a gateway-capable tmux session before live attach
- **WHEN** a developer launches a pair-managed TUI session through `houmao-srv-ctrl`
- **THEN** the runtime persists the actual tmux session name for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** the gateway capability artifacts are materialized through the shared runtime-owned gateway publication seam
- **AND THEN** window `0` is reserved as the primary agent surface for that session

#### Scenario: Current-session attach is unavailable before matching registration completes
- **WHEN** a delegated pair launch has already published stable gateway attachability into the tmux session
- **AND WHEN** managed-agent registration for that same persisted `api_base_url` and `session_name` has not yet completed successfully
- **THEN** the session is not yet current-session attach-ready
- **AND THEN** pair-managed current-session gateway attach fails closed rather than guessing another authority or alias

#### Scenario: Foreground auxiliary window does not retarget pair-managed execution
- **WHEN** a pair-managed `houmao_server_rest` session has an auxiliary gateway or diagnostics window selected in the foreground
- **AND WHEN** the runtime starts another controlled turn against that managed session
- **THEN** the controlled work still executes on the agent surface in window `0`
- **AND THEN** the runtime does not need to treat the selected auxiliary window as the authoritative agent surface

## ADDED Requirements

### Requirement: Supported pair-managed tmux sessions keep the agent in window 0 while auxiliary windows remain non-authoritative
For pair-managed tmux sessions that place gateway or other support processes in the same tmux session, the runtime SHALL reserve tmux window `0` for the agent process.

The runtime SHALL support that same-session auxiliary-window topology for `houmao_server_rest`.

The runtime SHALL keep the `houmao-server` process and its internal child-CAO support state outside the agent's tmux session even when the gateway sidecar runs inside the managed agent session.

Only tmux window `0` is contractual in that topology. The names, counts, and indices of non-zero tmux windows SHALL remain implementation details and SHALL NOT become part of the public attach or control contract.

Gateway attach, detach, crash cleanup, or auxiliary-window recreation SHALL NOT kill, replace, or repurpose the reserved agent window `0` during normal lifecycle handling.

If the agent process later disappears unexpectedly and the runtime relaunches it inside the same tmux session, the runtime SHALL restore the agent process to window `0` before treating the session as recovered or ready again.

#### Scenario: Pair-managed auxiliary window keeps the agent anchored to window 0
- **WHEN** a `houmao_server_rest` session runs a gateway or monitoring process in another tmux window
- **THEN** the agent process remains in window `0`
- **AND THEN** the non-zero process window does not become part of the public agent contract

#### Scenario: Same-session gateway topology keeps the server process out of the agent tmux session
- **WHEN** a pair-managed `houmao_server_rest` session runs a same-session gateway companion
- **THEN** only the gateway sidecar is introduced into an auxiliary tmux window of the managed agent session
- **AND THEN** the `houmao-server` process and child-CAO support state remain outside that tmux session

#### Scenario: Gateway lifecycle preserves the reserved agent window
- **WHEN** a same-session gateway process attaches, detaches, exits unexpectedly, or is recreated
- **THEN** the runtime only changes the auxiliary process window state
- **AND THEN** window `0` remains reserved for the agent surface throughout that sidecar lifecycle

#### Scenario: Relaunch restores the agent process to window 0
- **WHEN** an agent process in a supported same-session pair layout disappears unexpectedly and the runtime relaunches it in the existing tmux session
- **THEN** the runtime restores the relaunched agent process to window `0`
- **AND THEN** the session is not treated as recovered until that canonical agent surface is re-established
