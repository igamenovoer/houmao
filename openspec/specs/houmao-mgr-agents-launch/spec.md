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

### Requirement: `houmao-mgr agents launch` preserves recipe launch policy during local build
When `houmao-mgr agents launch` resolves a native recipe-backed target, it SHALL preserve the recipe's requested launch policy when building the brain manifest for local startup.

At minimum, recipe `launch_policy.operator_prompt_mode` SHALL be forwarded into brain construction so the built manifest and subsequent runtime launch use the same requested operator-prompt posture.

#### Scenario: Recipe unattended policy survives local `agents launch`
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **THEN** the local brain build records `launch_policy.operator_prompt_mode: unattended` in the built brain manifest
- **AND THEN** the local runtime launch uses that preserved unattended intent for the selected launch surface

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes
`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-attached) modes.

When `--headless` is specified, the agent SHALL run as a detached headless process.
When `--headless` is not specified, the agent SHALL start the selected provider's interactive terminal UI in a tmux session and the CLI SHALL attach to that tmux session.

#### Scenario: Headless launch runs detached
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux-backed headless session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to a live provider TUI
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **THEN** the agent starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session
- **AND THEN** the launch is not considered successful if the session falls back to an idle shell before the provider reaches its interactive ready posture

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

### Requirement: `houmao-mgr agents launch` resolves backend from provider and launch mode
`houmao-mgr agents launch` SHALL resolve the runtime launch surface from the provider identifier together with whether `--headless` was requested.

At minimum:
- headless `claude_code` launch uses the `claude_headless` backend
- headless `codex` launch uses the `codex_headless` backend
- headless `gemini_cli` launch uses the `gemini_headless` backend
- non-headless launch uses a local interactive runtime surface rather than a detached headless backend

#### Scenario: Headless Claude launch resolves to `claude_headless`
- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder --headless`
- **THEN** the agent is launched using the `claude_headless` backend

#### Scenario: Interactive Claude launch does not reuse the headless transport
- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder` without `--headless`
- **THEN** the agent is launched on the local interactive runtime surface
- **AND THEN** the session is treated as TUI transport rather than headless transport

#### Scenario: Unsupported provider is rejected
- **WHEN** an operator runs `houmao-mgr agents launch --provider unsupported_tool --agents gpu-kernel-coder`
- **THEN** the command fails with a clear error listing the supported providers

### Requirement: `houmao-mgr agents launch` reports unattended strategy compatibility failures distinctly
When local `houmao-mgr agents launch` requests a launch policy that must be resolved before provider startup, the command SHALL report launch-policy compatibility failures distinctly from backend-selection failures and post-start provider-runtime failures.

#### Scenario: Interactive Claude launch reports unattended version gap before provider startup
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the local interactive launch surface
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and local interactive launch surface
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the tmux-attached TUI became ready

#### Scenario: Headless Claude launch reports unattended version gap before provider startup
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the `claude_headless` backend
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and `claude_headless` backend
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the detached headless runtime session became live
