## MODIFIED Requirements

### Requirement: Demo pack SHALL provide wrapper scripts for the primary manual workflow
The interactive demo pack SHALL provide shell entrypoints for launching the
tutorial agent, sending one inline prompt, sending one control-input sequence,
and stopping the active session, while delegating behavior through the existing
`run_demo.sh` shell backend or a shared helper factored from it so the tutorial
commands inherit the same workspace and environment defaults as the advanced
interface.

The launch wrapper SHALL expose a supported repo-owned convenience invocation,
and it SHALL forward supported recipe-first startup arguments through the
shared startup path. If the wrapper contract changes as part of this refactor,
the repo's docs and tests SHALL be updated to the new supported form instead of
preserving the old one for compatibility.

For prompt, control-input, and stop flows that target the active session by
persisted agent identity, the underlying runtime invocations SHALL omit
explicit `--agent-def-dir` and rely on the runtime's name-addressed
tmux-session-derived default instead. Build/start flows may still pass explicit
`--agent-def-dir`.

#### Scenario: Launch wrapper applies its convenience agent-name override through the shared startup path
- **WHEN** a developer runs the launch wrapper from the demo pack without variant-selection flags
- **THEN** it starts or replaces the interactive session by passing `--agent-name alice`
- **AND** that override replaces the selected recipe's default agent name for that wrapper invocation
- **AND** it reuses the existing stateful lifecycle flow instead of implementing separate launch logic
- **AND** it preserves the same shell-level defaults and workspace state used by `run_demo.sh`

#### Scenario: Launch wrapper forwards explicit brain-recipe selection
- **WHEN** a developer runs the launch wrapper with a supported `--brain-recipe` selector
- **THEN** it forwards that argument through the shared `run_demo.sh start` path
- **AND** it still uses the same persisted workspace and state-management flow as the default tutorial launch

#### Scenario: Prompt wrapper forwards inline prompt text
- **WHEN** a developer runs the prompt wrapper with `--prompt <text>`
- **THEN** it sends the provided prompt through the active interactive session
- **AND** it targets the same persisted session identity recorded by launch

#### Scenario: Control-input wrapper forwards runtime sequences
- **WHEN** a developer runs the control-input wrapper with a required positional `<key-stream>`
- **THEN** it sends the provided control-input request through the active interactive session
- **AND** it targets the same persisted session identity recorded by launch
- **AND** it can pass through the runtime's `--as-raw-string` flag when requested

#### Scenario: Stop wrapper closes the active tutorial session
- **WHEN** a developer runs the stop wrapper after launching the tutorial agent
- **THEN** it invokes the interactive teardown flow for the active session
- **AND** the local demo state is updated so additional prompt attempts fail until the agent is launched again

#### Scenario: Wrapper commands stay aligned with the advanced shell interface
- **WHEN** a developer mixes the wrapper scripts with lower-level commands such as `run_demo.sh inspect`, `run_demo.sh send-keys`, or `run_demo.sh verify`
- **THEN** both command surfaces operate on the same persisted workspace and session state
- **AND** the wrapper scripts reuse the shell-level defaults already provided by `run_demo.sh` or a shared helper instead of duplicating them

#### Scenario: Repo-owned docs and tests move with wrapper contract changes
- **WHEN** the supported wrapper or startup invocation changes during this refactor
- **THEN** the repo updates its README examples, tests, and helper references to the new supported form
- **AND** the demo pack does not need to preserve the superseded invocation for backward compatibility

#### Scenario: Interactive demo prompt and control flows rely on the runtime tmux-session default
- **WHEN** a developer runs the interactive demo prompt, control-input, or stop workflow against an already-running session addressed by name
- **THEN** the underlying `realm_controller send-prompt`, `send-keys`, or `stop-session` invocation omits explicit `--agent-def-dir`
- **AND THEN** the workflow relies on the addressed tmux session's published `AGENTSYS_AGENT_DEF_DIR` value instead of the caller's cwd-derived agents root
