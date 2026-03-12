# cao-interactive-full-pipeline-demo Specification

## Purpose
TBD - created by archiving change add-interactive-cao-full-pipeline-demo. Update Purpose after archive.
## Requirements
### Requirement: Interactive demo session startup
The demo workflow SHALL provide a startup command that resolves a tracked brain
recipe, builds the selected Claude or Codex CAO runtime context from that
recipe, starts a `cao_rest` session with a role prompt, and writes a state
artifact containing the name-based session identity, inspection metadata, and
the resolved demo-variant metadata.

When the operator does not provide a recipe-selection override, startup SHALL
continue to use the current default Claude walkthrough by implicitly resolving
the tracked recipe `claude/gpu-kernel-coder-default`.

When the operator provides `--brain-recipe`, startup SHALL accept a supported
Claude or Codex brain-recipe selector and SHALL build the brain using the
matching recipe. Within this demo pack, the selector SHALL be resolved under
the fixed `brains/brain-recipes/` root beneath the active agent-definition
directory.

The demo SHALL resolve the requested selector to one canonical recipe file,
load that recipe through the shared recipe loader for startup metadata, and
invoke brain construction through the existing `brain_launch_runtime
build-brain --recipe <resolved-path>` path.

The selected recipe SHALL define the default agent name for the launch. When
the operator omits `--agent-name`, startup SHALL use that recipe-defined
default name. When the operator provides `--agent-name`, startup SHALL override
the recipe-defined default name before canonicalization to the persisted
`agent_identity`.

The selected recipe SHALL fully determine the launched brain composition for
this demo path, including `tool`, `skills`, `config_profile`,
`credential_profile`, and `default_agent_name`. The demo SHALL NOT override the
recipe's `skills`, `config_profile`, or `credential_profile` with demo-owned
defaults.

The selector SHALL treat the `.yaml` suffix as optional, so a selector such as
`claude/gpu-kernel-coder-default` SHALL resolve to the same recipe as
`claude/gpu-kernel-coder-default.yaml`, and
`codex/gpu-kernel-coder-default` SHALL resolve to the same recipe as
`codex/gpu-kernel-coder-default.yaml`.

Supported selectors SHALL include at minimum:

- `claude/gpu-kernel-coder-default`
- `gpu-kernel-coder-yunwu-openai`
- `codex/gpu-kernel-coder-yunwu-openai`
- `codex/gpu-kernel-coder-default`

The demo SHALL require exactly one matching recipe file for the requested
selector. If no recipe matches, startup SHALL fail with an explicit error. If
more than one recipe shares a basename, basename-only lookup SHALL fail with an
explicit ambiguity error, and a selector with subdirectory context SHALL be
accepted to disambiguate the launch.

The persisted state artifact SHALL include the previously required session
fields plus `tool`, `variant_id`, and the canonical `brain_recipe` selector
resolved for the launch, including the implicit default Claude launch.

`variant_id` SHALL equal the canonical `brain_recipe` selector with each `/`
replaced by `-`.

#### Scenario: Default startup uses the tracked Claude default recipe
- **WHEN** the user runs the interactive startup command without recipe-selection flags
- **THEN** the command builds the Claude runtime context from `claude/gpu-kernel-coder-default`
- **AND** the persisted state records the canonicalized `agent_identity` derived from the recipe-defined default agent name
- **AND** the persisted state records `tool = claude`
- **AND** the persisted state records `brain_recipe = claude/gpu-kernel-coder-default`
- **AND** the persisted state records `variant_id = claude-gpu-kernel-coder-default`

#### Scenario: Startup accepts the tracked Claude recipe explicitly
- **WHEN** the user runs the interactive startup command with brain recipe `claude/gpu-kernel-coder-default`
- **THEN** the command builds a Claude runtime context
- **AND** the persisted state records `tool = claude`
- **AND** the persisted state records `brain_recipe = claude/gpu-kernel-coder-default`
- **AND** the persisted state records `variant_id = claude-gpu-kernel-coder-default`

#### Scenario: Codex startup accepts the tracked default recipe with subdirectory context
- **WHEN** the user runs the interactive startup command with brain recipe `codex/gpu-kernel-coder-default`
- **THEN** the command builds a Codex runtime context
- **AND** the persisted state records `tool = codex`
- **AND** the persisted state records `brain_recipe = codex/gpu-kernel-coder-default`
- **AND** the persisted state records `variant_id = codex-gpu-kernel-coder-default`

#### Scenario: Codex startup accepts the tracked Yunwu recipe basename
- **WHEN** the user runs the interactive startup command with brain recipe `gpu-kernel-coder-yunwu-openai`
- **THEN** the command builds a Codex runtime context
- **AND** the persisted state records `tool = codex`
- **AND** the persisted state records `brain_recipe = codex/gpu-kernel-coder-yunwu-openai`
- **AND** the persisted state records `variant_id = codex-gpu-kernel-coder-yunwu-openai`

#### Scenario: Startup builds through the shared recipe path without demo-owned build overrides
- **WHEN** the user starts the interactive demo with any supported recipe selection
- **THEN** the demo invokes brain construction through the resolved `build-brain --recipe` path
- **AND** the selected recipe supplies the effective `skills`, `config_profile`, and `credential_profile`
- **AND** the demo does not substitute demo-owned defaults for those recipe fields

#### Scenario: Agent-name override replaces the recipe-defined default name
- **WHEN** the user runs the interactive startup command with a supported recipe and `--agent-name gpu-demo`
- **THEN** the command uses `gpu-demo` instead of the recipe-defined default agent name
- **AND** the persisted state records the canonicalized `agent_identity` derived from `gpu-demo`
- **AND** the selected recipe still determines the launched tool and brain composition

#### Scenario: Codex startup accepts the same recipe when `.yaml` is provided
- **WHEN** the user runs the interactive startup command with brain recipe `codex/gpu-kernel-coder-default.yaml`
- **THEN** the command resolves the same recipe as `codex/gpu-kernel-coder-default`
- **AND** the persisted state records the normalized recipe selector for that launch

#### Scenario: Claude startup accepts the same recipe when `.yaml` is provided
- **WHEN** the user runs the interactive startup command with brain recipe `claude/gpu-kernel-coder-default.yaml`
- **THEN** the command resolves the same recipe as `claude/gpu-kernel-coder-default`
- **AND** the persisted state records the normalized recipe selector for that launch

#### Scenario: Startup rejects ambiguous recipe basenames
- **WHEN** the requested brain-recipe basename matches more than one recipe file under the fixed recipe root
- **THEN** the command fails with an explicit ambiguity error
- **AND** it does not start a partial interactive session

#### Scenario: Startup accepts a disambiguating subdirectory selector after basename ambiguity
- **WHEN** `gpu-kernel-coder-default` matches more than one recipe file under the fixed recipe root
- **AND WHEN** the user retries with `claude/gpu-kernel-coder-default` or `codex/gpu-kernel-coder-default`
- **THEN** the command resolves the explicitly targeted recipe
- **AND** it proceeds with startup normally

#### Scenario: Startup fails safely when prerequisites are missing
- **WHEN** required runtime prerequisites for the selected variant are unavailable
- **THEN** the command exits with an explicit reason
- **AND** it does not create a partial interactive state marked as active

#### Scenario: Startup replaces a previously active demo session
- **WHEN** the user runs the interactive startup command while the state artifact already marks another demo session active
- **THEN** the command first attempts `brain_launch_runtime stop-session` for the recorded `agent_identity`
- **AND** the command starts a replacement session
- **AND** the state artifact is rewritten to the new `agent_identity` and the newly resolved variant metadata

#### Scenario: Startup replaces stale incompatible local state
- **WHEN** the interactive demo finds a previously persisted local state artifact that no longer validates under the current strict demo-state schema
- **THEN** startup treats that local state as stale
- **AND** it replaces the stale local state with freshly written state for the new launch instead of failing before startup completes

### Requirement: Follow-up demo commands SHALL reuse the persisted startup variant
Follow-up commands in the interactive demo workflow SHALL use the persisted state artifact as the source of truth for the selected tool and variant after startup completes.

`send-turn`, `send-keys`, `inspect`, `verify`, and `stop` SHALL continue to
operate on the active workspace and session without requiring the operator to
repeat the startup-time tool-selection arguments.

#### Scenario: Follow-up commands keep using the selected recipe-backed startup
- **WHEN** the user starts the interactive demo with one of the supported recipe selections
- **AND WHEN** they later run `send-turn`, `send-keys`, `inspect`, `verify`, or `stop` without repeating the startup selection flags
- **THEN** those commands operate on the persisted session recorded in state for that recipe-backed launch
- **AND** they do not fall back to a different recipe or tool

### Requirement: Verification artifacts SHALL preserve the selected demo variant
The interactive demo verification flow SHALL report the selected tool and
stable demo variant identity from the persisted workspace state.

The generated verification artifact SHALL preserve at minimum `tool`,
`variant_id`, `brain_recipe`, and the resolved session/workspace metadata
needed to connect the report to the active demo variant.

#### Scenario: Verification records the tool and variant used for the interactive run
- **WHEN** the user runs `run_demo.sh verify` after the minimum required interactive turns
- **THEN** `report.json` records the `tool` used for startup
- **AND** `report.json` records the stable `variant_id` resolved at startup
- **AND** `report.json` records the canonical `brain_recipe` resolved at startup
- **AND** the verification helper validates the report against the selected variant contract rather than assuming a fixed Claude-only snapshot

### Requirement: Multi-turn prompt driving against a live session
The demo workflow SHALL provide a turn-driving command that reads the persisted state artifact and sends a prompt through `brain_launch_runtime send-prompt` to the same active session by name-based `agent_identity`.

Operator interaction between automated turns MAY include manual slash commands or manual model switching inside the live session. Once the visible provider surface has returned to its normal prompt, the demo SHALL continue to treat that session as reusable for subsequent `send-turn` operations.

#### Scenario: Sequential prompts use one session identity
- **WHEN** the user runs the turn-driving command multiple times after a successful startup
- **THEN** each turn targets the same `agent_identity` recorded by startup
- **AND** each turn records a non-empty response in per-turn output artifacts along with the `agent_identity` used for that turn

#### Scenario: Follow-up send-turn still works after a recovered slash-command or model switch
- **WHEN** the operator uses a slash command or manual model switch inside the active interactive session between automated turns
- **AND WHEN** the live provider surface has already returned to its normal prompt before the next `send-turn`
- **THEN** the next `send-turn` reuses the same persisted `agent_identity`
- **AND THEN** it submits the prompt and records a normal turn artifact instead of hanging in readiness gating

#### Scenario: Turn-driving rejects missing or inactive session state
- **WHEN** the user runs the turn-driving command before startup or after stop
- **THEN** the command fails with a clear actionable message indicating that no active interactive session exists

### Requirement: Fixed local CAO target
The demo workflow SHALL use the fixed CAO base URL `http://127.0.0.1:9889` for startup and SHALL NOT depend on alternate CAO base URL inputs.

#### Scenario: Operator attempts to provide another CAO base URL
- **WHEN** the operator supplies a non-default CAO base URL input or environment override
- **THEN** the demo continues to use `http://127.0.0.1:9889`
- **AND** the effective startup metadata reflects the fixed loopback target

### Requirement: Live inspection affordances
The demo workflow SHALL expose enough metadata for live tmux and log inspection while the session remains active.

#### Scenario: User can attach and observe
- **WHEN** startup completes
- **THEN** the workflow outputs or stores a tmux attach target derived from session metadata
- **AND** the workflow outputs or stores a terminal log path suitable for tailing CAO output

### Requirement: Explicit interactive teardown
The demo workflow SHALL provide an explicit stop command that terminates the active interactive session and marks the state as no longer active.

#### Scenario: Stop cleans up active session
- **WHEN** the user runs the stop command with an active state artifact
- **THEN** the command calls `brain_launch_runtime stop-session` for the recorded `agent_identity`
- **AND** subsequent turn-driving attempts fail until startup is run again

#### Scenario: Stop is safe when session is already gone
- **WHEN** the recorded session no longer exists remotely
- **THEN** the command exits gracefully and updates local state to inactive

### Requirement: Live control-input driving against an active session
The demo workflow SHALL provide a `send-keys` command that reads the persisted state artifact and sends a raw control-input sequence through `brain_launch_runtime send-keys` to the same active session by name-based `agent_identity`.

The operator-facing control-input workflow SHALL require one positional key-stream input, and it SHALL forward the runtime-owned `send-keys` contract without appending implicit submit behavior.

#### Scenario: Control input targets the active persisted session
- **WHEN** the user runs the control-input command after a successful startup
- **THEN** the command targets the same `agent_identity` recorded in the active state artifact
- **AND** it sends the requested sequence through `brain_launch_runtime send-keys`

#### Scenario: Control input rejects missing or inactive session state
- **WHEN** the user runs the control-input command before startup or after stop
- **THEN** the command fails with a clear actionable message indicating that no active interactive session exists

#### Scenario: Control input forwards the runtime sequence contract
- **WHEN** the user runs the control-input command with a required positional key stream
- **THEN** the demo forwards the provided sequence to the runtime `send-keys` path without reinterpreting the runtime's mixed text or special-key grammar
- **AND** it does not add an implicit trailing `Enter`

#### Scenario: Control input can request raw-string mode
- **WHEN** the user runs the control-input command with `--as-raw-string`
- **THEN** the demo forwards that flag to the runtime `send-keys` path
- **AND** token-like substrings are treated according to the runtime's raw-string mode

### Requirement: Control-input artifacts remain distinct from prompt-turn verification
The demo workflow SHALL persist control-input artifacts separately from prompt-turn artifacts and SHALL NOT count control-input actions as prompt turns for verification.

#### Scenario: Control input writes separate artifacts
- **WHEN** the user runs the control-input command
- **THEN** the demo writes a structured control-input record plus captured stdout and stderr logs under a dedicated artifact family separate from `turns/`
- **AND** existing prompt-turn artifacts remain unchanged

#### Scenario: Verification remains prompt-turn-only after control input
- **WHEN** the user runs one or more control-input actions between prompt turns and later runs `verify`
- **THEN** the generated verification report is derived only from recorded prompt-turn artifacts
- **AND** it does not require or count control-input artifacts as turns
