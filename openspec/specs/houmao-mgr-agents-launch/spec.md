# houmao-mgr-agents-launch Specification

## Purpose
Define the local `houmao-mgr agents launch` contract for brain construction and runtime startup without requiring `houmao-server`.

## Requirements

### Requirement: `houmao-mgr agents launch` performs local brain building and agent launch

`houmao-mgr agents launch` SHALL perform the full agent launch pipeline locally without requiring a running `houmao-server`.

The pipeline SHALL follow this sequence:
1. Parse the `agents/` source tree into the canonical parsed catalog.
2. Resolve the native launch target from the `--agents` selector and `--provider` against that parsed catalog.
3. Resolve the selected preset to its effective tool, role, setup, skills, launch settings, and effective auth as one resolved launch/build specification.
4. Build the brain home from that resolved build specification.
5. Start the runtime session via `start_runtime_session()`.
6. Publish a `LiveAgentRegistryRecordV2` to the shared registry.

#### Scenario: Operator launches an agent without houmao-server

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** no `houmao-server` is running
- **THEN** `houmao-mgr` parses the source tree, resolves the preset from the parsed catalog, builds the brain home, starts the session, and publishes to the shared registry
- **AND THEN** the agent is running and discoverable via the shared registry

#### Scenario: Launched agent appears in shared registry

- **WHEN** an operator runs a successful `houmao-mgr agents launch`
- **THEN** the shared registry at `~/.houmao/registry/live_agents/` contains a `LiveAgentRegistryRecordV2` for the launched agent
- **AND THEN** the record includes `identity.backend`, `identity.tool`, `runtime.manifest_path`, and `terminal.session_name`

#### Scenario: Launch fails clearly when preset is not found

- **WHEN** an operator runs `houmao-mgr agents launch --agents nonexistent --provider claude_code`
- **THEN** the command fails with a clear error message indicating the preset could not be resolved
- **AND THEN** no partial brain home or registry record is left behind

### Requirement: `houmao-mgr agents launch` accepts the established launch options

`houmao-mgr agents launch` SHALL accept at minimum:

- `--agents` (required): Native launch selector to resolve the preset
- `--provider` (required or defaulted): Provider identifier (`claude_code`, `codex`, `gemini_cli`, etc.)
- `--agent-name`: Optional logical managed-agent name
- `--agent-id`: Optional authoritative managed-agent identifier
- `--auth`: Optional auth override for the resolved preset
- `--session-name`: Optional tmux session name (auto-generated if omitted)
- `--headless`: Launch in detached mode
- `--yolo`: Skip workspace trust confirmation

#### Scenario: Operator specifies a custom session name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --session-name my-agent`
- **THEN** the tmux session is created with the name `my-agent`

#### Scenario: Operator overrides preset auth

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --auth kimi-coding`
- **AND WHEN** the resolved preset would otherwise use a different default auth selection
- **THEN** the launch uses auth bundle `kimi-coding`
- **AND THEN** the built manifest records `kimi-coding` as the effective auth selection

#### Scenario: Operator supplies an explicit managed-agent name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a`
- **THEN** the launch uses `worker-a` as the managed-agent logical name
- **AND THEN** the preset does not need to define any default managed-agent name

#### Scenario: Workspace trust confirmation is shown for providers that access the workspace

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--yolo`
- **THEN** the CLI displays a workspace trust confirmation prompt before launching
- **AND THEN** the operator can decline to cancel the launch

#### Scenario: Workspace trust confirmation is skipped with --yolo

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --yolo`
- **THEN** the CLI skips the workspace trust confirmation and launches immediately

### Requirement: `houmao-mgr agents launch` resolves preset selectors with explicit default-setup behavior

`houmao-mgr agents launch` SHALL support exactly two preset selector forms on `--agents`:

- bare role selector `<role>`, resolved together with the provider-derived tool to `agents/roles/<role>/presets/<tool>/default.yaml`
- explicit preset file path

The command SHALL NOT interpret `<role>/<setup>` as selector shorthand in this change.

#### Scenario: Bare role selector resolves the default setup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command SHALL resolve `agents/roles/gpu-kernel-coder/presets/claude/default.yaml`

#### Scenario: Explicit preset path selects a non-default setup

- **WHEN** an operator runs `houmao-mgr agents launch --agents agents/roles/gpu-kernel-coder/presets/codex/yunwu-openai.yaml --provider codex`
- **THEN** the command SHALL resolve that explicit preset file path directly

#### Scenario: Hybrid role-setup shorthand is rejected

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder/research --provider claude_code`
- **THEN** the command SHALL NOT reinterpret that selector as `<role>/<setup>`
- **AND THEN** it SHALL fail clearly unless that input resolves as an explicit preset file path

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes

`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-backed TUI) modes.

When `--headless` is specified, the agent SHALL run as a detached headless process.

When `--headless` is not specified, the agent SHALL start the selected provider's interactive terminal UI in a tmux session.

When `--headless` is not specified and the caller provides a usable interactive terminal, the CLI SHALL perform the operator handoff to that tmux session through the repo-owned tmux integration boundary rather than through an ad hoc raw tmux subprocess call.

When `--headless` is not specified and the caller does not provide a usable interactive terminal, the command SHALL still be considered successful once the runtime session is live and the provider reaches the required ready posture, SHALL NOT attempt a terminal attach that can fail solely because the caller is non-interactive, and SHALL surface enough tmux identity for a later manual attach.

Interactive or non-interactive launch SHALL still fail if the session falls back to an idle shell before the provider reaches its interactive ready posture.

#### Scenario: Headless launch runs detached

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux-backed headless session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to a live provider TUI when the caller is interactive

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has a usable interactive terminal
- **THEN** the agent starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session through the repo-owned tmux integration path
- **AND THEN** the launch is not considered successful if the session falls back to an idle shell before the provider reaches its interactive ready posture

#### Scenario: Non-interactive caller does not turn a successful launch into a false attach failure

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has no usable interactive terminal
- **THEN** the agent still starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the command reports launch success without attempting a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** the output still surfaces the tmux session identity needed for a later manual attach

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

When local `houmao-mgr agents launch` requests launch settings that must be resolved before provider startup, the command SHALL report launch-policy compatibility failures distinctly from backend-selection failures and post-start provider-runtime failures.

#### Scenario: Interactive Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the selected preset requests `launch.prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the local interactive launch surface
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and local interactive launch surface
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the tmux-attached TUI became ready

#### Scenario: Headless Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **AND WHEN** the selected preset requests `launch.prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the `claude_headless` backend
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and `claude_headless` backend
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the detached headless runtime session became live

### Requirement: `houmao-mgr agents launch` preserves preset launch settings during local build

When `houmao-mgr agents launch` resolves a native preset-backed target from the canonical parsed catalog, it SHALL preserve the preset's requested launch settings when building the brain manifest for local startup.

At minimum, preset `launch.prompt_mode` and preset `launch.overrides` SHALL be forwarded into brain construction so the built manifest and subsequent runtime launch use the same requested launch posture and overrides.

#### Scenario: Preset unattended policy survives local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected preset requests `launch.prompt_mode: unattended`
- **THEN** the local brain build records the equivalent unattended operator-prompt intent in the built brain manifest
- **AND THEN** the local runtime launch uses that preserved unattended intent for the selected launch surface

#### Scenario: Preset launch overrides survive local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex`
- **AND WHEN** the selected preset requests `launch.overrides.tool_params`
- **THEN** the local brain build records the equivalent launch overrides in the built manifest
- **AND THEN** the local runtime launch uses those preserved overrides for the selected tool

### Requirement: `houmao-mgr agents launch` keeps managed-agent identity launch-time only

Preset-backed launch SHALL NOT depend on preset-owned default managed-agent names. `--agent-name` and `--agent-id` SHALL remain optional launch-time inputs.

When `--agent-name` is omitted, the runtime SHALL derive the fallback managed-agent logical name from tool plus role using the existing runtime auto-name path. Operators who need multiple distinct concurrently managed logical agents from the same preset SHALL provide explicit `--agent-name` values.

#### Scenario: Launch succeeds without an explicit managed-agent name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the preset does not define any managed-agent name
- **THEN** the runtime SHALL derive the logical managed-agent name from the resolved tool and role
- **AND THEN** the launch SHALL succeed without requiring any preset-owned identity field

#### Scenario: Distinct concurrent logical agents require explicit names

- **WHEN** an operator needs two distinct concurrently managed logical agents from the same preset
- **THEN** the operator SHALL provide distinct `--agent-name` values for those launches
- **AND THEN** the system SHALL treat those explicit names, not the preset path, as the distinguishing logical identities

### Requirement: `houmao-mgr agents launch` consumes the canonical parsed contract

`houmao-mgr agents launch` SHALL consume canonical parsed definitions or one derived resolved launch specification rather than reading user-facing source files directly inside downstream launch and build stages.

#### Scenario: Source-layout parsing stays upstream of launch and build

- **WHEN** `houmao-mgr agents launch` handles one operator request
- **THEN** any source-layout-specific parsing SHALL happen before downstream launch and build logic consumes the resolved inputs
- **AND THEN** builder and runtime stages SHALL operate on canonical parsed data rather than on raw source mappings

### Requirement: `houmao-mgr agents launch` accepts user-specified agent identity fields

`houmao-mgr agents launch` SHALL accept optional managed-agent identity inputs for launch-time publication.

At minimum:

- `--agent-name <name>` MAY be supplied
- `--agent-id <id>` MAY be supplied

When the caller omits `--agent-name`, the launch path SHALL allow runtime identity derivation from the resolved tool and role using the existing runtime auto-name path.

When the caller omits `--agent-id` and an effective managed-agent name exists, the launch path SHALL derive the effective authoritative identity as `md5(agent_name).hexdigest()`.

The launch path SHALL validate explicit `agent_name` and `agent_id` values against the shared registry's filesystem-safe and URL-safe identity rules before publishing the live record.

#### Scenario: Launch accepts explicit friendly name and authoritative id

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu --agent-id gpu-prod-001 --yolo`
- **THEN** the launch path publishes the managed agent with friendly name `gpu` and authoritative id `gpu-prod-001`
- **AND THEN** later exact control may target that agent by `--agent-id gpu-prod-001`

#### Scenario: Launch derives authoritative id when omitted

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu --yolo`
- **THEN** the launch path derives the effective authoritative identity as `md5("gpu").hexdigest()`
- **AND THEN** the published live record uses that derived value as `agent_id`

### Requirement: `houmao-mgr agents launch` reports managed-agent and tmux identities separately

When `houmao-mgr agents launch` completes successfully, the command SHALL report the managed-agent identity fields separately from the tmux session handle used to host the live terminal surface.

At minimum, the successful launch output SHALL surface:

- the effective `agent_name` for later `houmao-mgr agents ...` commands
- the authoritative `agent_id`
- the actual `tmux_session_name`
- the `manifest_path`

When the operator supplied `--session-name`, that value SHALL remain the tmux session handle only unless it independently matches the chosen managed-agent name by coincidence. The launch output SHALL make that distinction visible to the operator.

When the operator did not supply `agent_id`, the launch path SHALL surface the effective derived `agent_id` used for publication and later exact addressing.

#### Scenario: Interactive launch prints control ref and tmux session distinctly

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --session-name hm-gw-track-codex --yolo`
- **THEN** the successful launch output includes the effective `agent_name`, the authoritative `agent_id`, the tmux session name `hm-gw-track-codex`, and the manifest path
- **AND THEN** the output makes clear which value to use for later managed-agent commands versus tmux attach operations

#### Scenario: Custom session name does not redefine the managed-agent ref

- **WHEN** an operator launches a managed agent with `--session-name my-custom-tmux-name`
- **AND WHEN** the runtime publishes a different managed-agent name in the shared registry
- **THEN** the launch output shows both values distinctly
- **AND THEN** `my-custom-tmux-name` is not implied to have replaced the managed-agent name

#### Scenario: Omitted agent id reports the derived effective identity

- **WHEN** an operator launches a managed agent without supplying `agent_id`
- **THEN** the launch output includes the effective `agent_id = md5(agent_name).hexdigest()`
- **AND THEN** the operator can use that derived `agent_id` for later exact disambiguation if needed
