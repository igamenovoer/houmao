## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` accepts the established launch options

`houmao-mgr agents launch` SHALL accept at minimum:

- `--agents` (required): Native launch selector to resolve the preset
- `--provider` (required or defaulted): Provider identifier (`claude_code`, `codex`, `gemini_cli`, etc.)
- `--agent-name`: Optional logical managed-agent name
- `--agent-id`: Optional authoritative managed-agent identifier
- `--auth`: Optional auth override for the resolved preset
- `--session-name`: Optional tmux session name (auto-generated if omitted)
- `--headless`: Launch in detached mode

The command SHALL NOT expose a separate CLI workspace-trust bypass flag on this surface.

The command SHALL proceed without a Houmao-managed workspace trust confirmation prompt before local launch begins.

The effective provider startup posture SHALL remain determined by the resolved preset `launch.prompt_mode` together with the downstream runtime/provider launch-policy contract.

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

#### Scenario: Local launch does not require a separate workspace-trust bypass flag

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command proceeds without a Houmao-managed workspace trust confirmation prompt
- **AND THEN** any no-prompt or full-autonomy startup posture comes from the resolved `launch.prompt_mode` rather than from a separate `--yolo` flag

### Requirement: `houmao-mgr agents launch` accepts user-specified agent identity fields

`houmao-mgr agents launch` SHALL accept optional managed-agent identity inputs for launch-time publication.

At minimum:

- `--agent-name <name>` MAY be supplied
- `--agent-id <id>` MAY be supplied

When the caller omits `--agent-name`, the launch path SHALL allow runtime identity derivation from the resolved tool and role using the existing runtime auto-name path.

When the caller omits `--agent-id` and an effective managed-agent name exists, the launch path SHALL derive the effective authoritative identity as `md5(agent_name).hexdigest()`.

The launch path SHALL validate explicit `agent_name` and `agent_id` values against the shared registry's filesystem-safe and URL-safe identity rules before publishing the live record.

#### Scenario: Launch accepts explicit friendly name and authoritative id

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu --agent-id gpu-prod-001`
- **THEN** the launch path publishes the managed agent with friendly name `gpu` and authoritative id `gpu-prod-001`
- **AND THEN** later exact control may target that agent by `--agent-id gpu-prod-001`

#### Scenario: Launch derives authoritative id when omitted

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu`
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

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --session-name hm-gw-track-codex`
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
