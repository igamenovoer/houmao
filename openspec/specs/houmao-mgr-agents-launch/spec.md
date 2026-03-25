## Purpose
Define the local `houmao-mgr agents launch` contract for brain construction and runtime startup without requiring `houmao-server`.

## Requirements

### Requirement: `houmao-mgr agents launch` performs local brain building and agent launch
`houmao-mgr agents launch` SHALL perform the full agent launch pipeline locally without requiring a running `houmao-server`.

The pipeline SHALL follow this sequence:
1. Resolve the native launch target from the `--agents` selector and `--provider`
2. Build the brain home via `build_brain_home(BuildRequest(...))`
3. Start the runtime session via `start_runtime_session()`
4. Publish a `LiveAgentRegistryRecordV2` to the shared registry

#### Scenario: Operator launches an agent without houmao-server
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** no `houmao-server` is running
- **THEN** `houmao-mgr` resolves the recipe, builds the brain home, starts the session, and publishes to the shared registry
- **AND THEN** the agent is running and discoverable via the shared registry

#### Scenario: Launched agent appears in shared registry
- **WHEN** an operator runs a successful `houmao-mgr agents launch`
- **THEN** the shared registry at `~/.houmao/registry/live_agents/` contains a `LiveAgentRegistryRecordV2` for the launched agent
- **AND THEN** the record includes `identity.backend`, `identity.tool`, `runtime.manifest_path`, and `terminal.session_name`

#### Scenario: Launch fails clearly when recipe is not found
- **WHEN** an operator runs `houmao-mgr agents launch --agents nonexistent --provider claude_code`
- **THEN** the command fails with a clear error message indicating the recipe could not be resolved
- **AND THEN** no partial brain home or registry record is left behind

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes
`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-attached) modes.

When `--headless` is specified, the agent SHALL run as a headless background process.
When `--headless` is not specified, the agent SHALL run in a tmux session and the CLI SHALL attach to that tmux session.

#### Scenario: Headless launch runs detached
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to tmux
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **THEN** the agent starts in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session

### Requirement: `houmao-mgr agents launch` accepts the established launch options
`houmao-mgr agents launch` SHALL accept at minimum:

- `--agents` (required): Native launch selector to resolve the brain recipe
- `--provider` (required or defaulted): Provider identifier (claude_code, codex, gemini_cli, etc.)
- `--session-name`: Optional tmux session name (auto-generated if omitted)
- `--headless`: Launch in detached mode
- `--yolo`: Skip workspace trust confirmation

#### Scenario: Operator specifies a custom session name
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --session-name my-agent`
- **THEN** the tmux session is created with the name `my-agent`

#### Scenario: Workspace trust confirmation is shown for providers that access the workspace
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--yolo`
- **THEN** the CLI displays a workspace trust confirmation prompt before launching
- **AND THEN** the operator can decline to cancel the launch

#### Scenario: Workspace trust confirmation is skipped with --yolo
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --yolo`
- **THEN** the CLI skips the workspace trust confirmation and launches immediately

### Requirement: `houmao-mgr agents launch` resolves backend from provider
`houmao-mgr agents launch` SHALL resolve the runtime backend from the provider identifier using the same mapping as the existing launch infrastructure.

At minimum:
- `claude_code` -> `claude_headless` backend
- `codex` -> `codex_headless` backend
- `gemini_cli` -> `gemini_headless` backend

#### Scenario: Claude provider resolves to claude_headless backend
- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents ...`
- **THEN** the agent is launched using the `claude_headless` backend

#### Scenario: Unsupported provider is rejected
- **WHEN** an operator runs `houmao-mgr agents launch --provider unsupported_tool --agents ...`
- **THEN** the command fails with a clear error listing the supported providers
