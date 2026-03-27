## MODIFIED Requirements

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

## ADDED Requirements

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
`houmao-mgr agents launch` SHALL consume canonical parsed definitions or one derived resolved launch specification rather than reading user-facing source files directly inside downstream launch/build stages.

#### Scenario: Source-layout parsing stays upstream of launch/build
- **WHEN** `houmao-mgr agents launch` handles one operator request
- **THEN** any source-layout-specific parsing SHALL happen before downstream launch/build logic consumes the resolved inputs
- **AND THEN** builder and runtime stages SHALL operate on canonical parsed data rather than on raw source mappings

## REMOVED Requirements

### Requirement: `houmao-mgr agents launch` preserves recipe launch policy during local build
**Reason**: Launch policy is now owned by presets rather than by a separate recipe layer.

**Migration**: Read launch settings from the resolved preset and forward them during brain construction using the new preset-backed contract.
