# cao-interactive-demo-operator-workflow Specification

## Purpose
TBD - created by archiving change revise-cao-interactive-demo-tutorial-and-wrappers. Update Purpose after archive.
## Requirements
### Requirement: Tutorial README SHALL present the interactive CAO demo as a step-by-step operator workflow
The demo pack README SHALL follow the repository's API usage tutorial style and explain the interactive workflow in a human-oriented sequence instead of only listing lifecycle commands.

#### Scenario: README documents the primary interactive journey
- **WHEN** a developer opens the interactive demo README
- **THEN** it presents a concrete question or goal for the tutorial
- **AND** it includes a prerequisites checklist, a short implementation idea, and step-by-step sections for launch, inspection, prompt interaction, control-input interaction, and stop
- **AND** each critical step includes an inline fenced code block showing the exact command to run

### Requirement: Demo pack SHALL provide wrapper scripts for the primary manual workflow
The interactive demo pack SHALL provide shell entrypoints for launching the tutorial agent, sending one inline prompt, sending one control-input sequence, and stopping the active session, while delegating behavior through the existing `run_demo.sh` shell backend or a shared helper factored from it so the tutorial commands inherit the same workspace and environment defaults as the advanced interface.

#### Scenario: Launch wrapper starts the tutorial agent as alice
- **WHEN** a developer runs the launch wrapper from the demo pack
- **THEN** it starts or replaces the interactive session using the agent identity `alice`
- **AND** it reuses the existing stateful lifecycle flow instead of implementing separate launch logic
- **AND** it preserves the same shell-level defaults and workspace state used by `run_demo.sh`

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
- **WHEN** a developer mixes the new wrapper scripts with lower-level commands such as `run_demo.sh inspect`, `run_demo.sh send-keys`, or `run_demo.sh verify`
- **THEN** both command surfaces operate on the same persisted workspace and session state
- **AND** the wrapper scripts reuse the shell-level defaults already provided by `run_demo.sh` or a shared helper instead of duplicating them

### Requirement: Main tutorial flow SHALL be open-ended rather than verification-driven
The interactive demo tutorial SHALL describe launch, repeated prompt sending, optional control-input sending, inspection, and explicit stop as the main operator flow, and SHALL NOT require the reader to run report verification as part of the primary walkthrough.

#### Scenario: Verification is documented as secondary tooling
- **WHEN** a developer follows the README's main walkthrough
- **THEN** the documented happy path may alternate manual prompts and manual control-input actions before the user explicitly stops the interactive session
- **AND** any `verify` or snapshot-report instructions are placed in a clearly secondary appendix or maintainer-focused section
- **AND** that section explains that `verify` remains an optional minimum two-turn maintainer check even after additional manual prompts or control-input actions

### Requirement: README appendix SHALL make the tutorial easy to rerun and debug
The tutorial README SHALL include an appendix describing the key parameters, tracked inputs, generated outputs, and supporting source files used by the interactive demo pack, including the control-input wrapper and the dedicated control artifact family.

#### Scenario: Appendix enumerates important files and parameters
- **WHEN** a developer wants to inspect or rerun the tutorial environment
- **THEN** the README lists the fixed CAO base URL, the tutorial agent identity, the default workspace location, and the main wrapper or CLI entrypoints including the control-input wrapper
- **AND** the README identifies the relevant input files, generated workspace files including control-input artifacts, and supporting implementation files for debugging
- **AND** it notes that the wrapper-friendly name `alice` is persisted through the engine's canonicalized agent identity for inspection and debugging output
