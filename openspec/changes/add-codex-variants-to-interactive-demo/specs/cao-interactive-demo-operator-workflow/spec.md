## MODIFIED Requirements

### Requirement: Tutorial README SHALL present the interactive CAO demo as a step-by-step operator workflow
The demo pack README SHALL follow the repository's API usage tutorial style and explain the interactive workflow in a human-oriented sequence instead of only listing lifecycle commands.

The README SHALL present the supported recipe-first contract for the interactive demo as the source of truth. The repo does not need backward-compatible documentation for superseded demo call shapes; instead, the README SHALL document the supported recipe-based Claude and Codex launches from the same demo pack.

#### Scenario: README documents the primary interactive journey and the supported recipe choices
- **WHEN** a developer opens the interactive demo README
- **THEN** it presents a concrete question or goal for the tutorial
- **AND** it includes a prerequisites checklist, a short implementation idea, and step-by-step sections for launch, inspection, prompt interaction, control-input interaction, and stop
- **AND** it identifies the default Claude startup path as an implicit launch of `claude/gpu-kernel-coder-default`
- **AND** it explains that direct `run_demo.sh start` uses tool-specific recipe-defined default agent names unless the operator supplies `--agent-name`
- **AND** it explains that `--agent-name` overrides the selected recipe's default agent name rather than selecting a demo-owned special identity
- **AND** it documents the supported explicit recipe-based startup examples using selectors relative to the fixed recipe root, with optional subdirectories and optional `.yaml`
- **AND** each critical step includes an inline fenced code block showing the exact command to run

### Requirement: Demo pack SHALL provide wrapper scripts for the primary manual workflow
The interactive demo pack SHALL provide shell entrypoints for launching the tutorial agent, sending one inline prompt, sending one control-input sequence, and stopping the active session, while delegating behavior through the existing `run_demo.sh` shell backend or a shared helper factored from it so the tutorial commands inherit the same workspace and environment defaults as the advanced interface.

The launch wrapper SHALL expose a supported repo-owned convenience invocation, and it SHALL forward supported recipe-first startup arguments through the shared startup path. If the wrapper contract changes as part of this refactor, the repo's docs and tests SHALL be updated to the new supported form instead of preserving the old one for compatibility.

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

### Requirement: README appendix SHALL make the tutorial easy to rerun and debug
The tutorial README SHALL include an appendix describing the key parameters, tracked inputs, generated outputs, supported startup recipes, and supporting source files used by the interactive demo pack, including the control-input wrapper and the dedicated control artifact family.

#### Scenario: Appendix enumerates important files, parameters, and recipe choices
- **WHEN** a developer wants to inspect or rerun the tutorial environment
- **THEN** the README lists the fixed CAO base URL, the tutorial agent identity, the default workspace location, and the main wrapper or CLI entrypoints including the control-input wrapper
- **AND** it identifies the default Claude launch as the tracked recipe `claude/gpu-kernel-coder-default`
- **AND** it identifies the supported explicit `--brain-recipe` examples without requiring the `brains/brain-recipes/` prefix
- **AND** it explains that direct `run_demo.sh start` uses the selected recipe's default agent name unless the operator supplies `--agent-name`
- **AND** it explains that subdirectory context may be required when recipe basenames collide, such as the shared `gpu-kernel-coder-default` basename for Claude and Codex
- **AND** it includes an explicit ambiguity-error example that tells the operator to retry with subdirectory context when basename-only lookup matches more than one recipe
- **AND** the README identifies the relevant input files, generated workspace files including control-input artifacts, and supporting implementation files for debugging
- **AND** it notes that `launch_alice.sh` is only a convenience wrapper that injects `--agent-name alice` rather than the source of the demo's default naming semantics
