## MODIFIED Requirements

### Requirement: Headless Claude/Gemini/Codex sessions are tmux-backed and inspectable
For headless sessions of tmux-backed CLI tools (at minimum Claude Code, Gemini, and Codex), the runtime SHALL create and own a tmux session per started session.

The runtime SHALL choose and persist one tmux session name per started session as a unique live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window 0 as the primary agent surface for that session and SHALL keep the headless agent itself on that primary surface across runtime-controlled turns.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

Auxiliary windows MAY exist later in the same tmux session for gateway, logs, or operator diagnostics, but they SHALL NOT displace the agent from window 0 and SHALL NOT redefine the primary headless attach surface.

#### Scenario: Start a headless session creates a tmux identity with manifest pointer and primary agent window
- **WHEN** a developer starts a headless Codex, Claude, or Gemini session without CAO
- **THEN** the runtime creates a tmux-backed live session and persists its actual tmux session name as metadata for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH` pointing at the persisted session manifest JSON
- **AND THEN** window 0 is reserved as the primary agent surface for that session

#### Scenario: Auxiliary windows do not replace the primary agent surface
- **WHEN** a tmux-backed headless session later creates another window for gateway, logs, or operator diagnostics
- **THEN** the headless agent remains anchored to window 0
- **AND THEN** callers can continue treating window 0 as the canonical attach surface for that headless agent

## ADDED Requirements

### Requirement: Tmux-backed headless turns reuse the primary agent window
For one tmux-backed headless session, runtime-controlled prompt execution SHALL be serialized and SHALL NOT overlap.

The runtime SHALL execute each runtime-controlled headless turn on the stable primary agent surface in window 0 and SHALL NOT create a separate per-turn tmux window for normal turn execution.

Turn identity, stdout, stderr, exit status, and process metadata SHALL remain per-turn durable artifacts on disk rather than being encoded through tmux window allocation.

#### Scenario: Active headless turn runs on the primary agent surface
- **WHEN** the runtime starts a controlled turn for a tmux-backed headless session
- **THEN** that turn executes on the stable window-0 agent surface
- **AND THEN** rolling output remains visible on that same primary surface
- **AND THEN** the runtime does not create a separate per-turn tmux window for that turn

#### Scenario: Runtime-controlled headless turns do not overlap in one session
- **WHEN** one runtime-controlled headless turn is already active for a tmux-backed session
- **AND WHEN** another runtime-controlled prompt is addressed to that same live session before the first turn reaches terminal state
- **THEN** the runtime does not start a second overlapping CLI execution for that session
- **AND THEN** window 0 remains the only runtime-controlled execution surface for that headless agent
