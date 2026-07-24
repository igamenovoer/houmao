# docs-launch-policy-reference Specification

## Purpose
Define the documentation requirements for the launch policy reference page.
## Requirements
### Requirement: Launch policy reference page exists

The build-phase reference SHALL include a page at `docs/reference/build-phase/launch-policy.md` documenting the launch policy engine. The page SHALL explain:

- What a launch policy is: a set of rules that govern agent behavior during the run phase, including operator prompt mode, auto-approval settings, and provider-specific constraints.
- The `OperatorPromptMode` enum: the available prompt modes and what each means for agent autonomy and operator involvement.
- Provider hooks: how launch policies can include provider-specific hooks that customize behavior for Claude, Codex, or Gemini backends, including strategy-owned startup surfaces such as Gemini unattended approval mode and sandbox posture. The Codex hooks table SHALL include `codex.append_unattended_cli_overrides`, which appends final Codex CLI `-c` override arguments for unattended-owned surfaces so project-local `config.toml` cannot weaken the strategy-owned unattended posture.
- The versioned registry: how launch policies are stored and resolved from `agents/launch_policy/registry/`, with version-based selection.
- Integration with the build phase: how launch policies are resolved during `BrainBuilder.build()` and included in the `BrainManifest`.
- Maintained unattended ownership: how launch policies may replace conflicting caller or copied-baseline startup inputs so the final provider launch matches the maintained unattended contract.

The page SHALL be derived from `agents/launch_policy/models.py`, `agents/launch_policy/engine.py`, `agents/launch_policy/provider_hooks.py`, and `agents/launch_policy/registry/`.

#### Scenario: Reader understands launch policy purpose

- **WHEN** a reader opens the launch policy page
- **THEN** they find a clear explanation of launch policies as run-phase behavioral constraints resolved during the build phase
- **AND THEN** they understand that policies control agent autonomy, prompt modes, and provider-specific behavior

#### Scenario: Reader can identify available prompt modes

- **WHEN** a reader wants to configure agent autonomy
- **THEN** the page documents the `OperatorPromptMode` values with descriptions of each mode's operator involvement level

#### Scenario: Reader understands policy resolution

- **WHEN** a reader wants to understand how a policy is selected
- **THEN** the page explains the resolution chain: preset-specified policy → versioned registry lookup → default policy
- **AND THEN** the page describes how provider hooks customize the resolved policy for specific backends

#### Scenario: Reader understands Gemini unattended launch ownership

- **WHEN** a reader wants to understand why maintained Gemini unattended headless launch does not follow Gemini's default non-interactive read-only posture
- **THEN** the page explains that launch policy owns Gemini unattended approval and sandbox startup surfaces
- **AND THEN** the page makes clear that maintained unattended Gemini startup may replace conflicting caller or copied-baseline inputs to preserve the documented no-ask full-permission posture

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode
The launch policy reference SHALL document separate maintained Kimi 0.23.x backend contracts for `kimi_headless` and for Kimi Code TUI through the `raw_launch` launch-policy surface.

The reference SHALL explain that Kimi headless prompt mode remains incompatible with passing `--auto`, `--yolo`, or `--plan`, while Kimi TUI unattended launch uses native `--auto` for fresh and resumed startup. It SHALL state that Houmao does not submit `/auto on` as a conversational bootstrap command.

The reference SHALL state that Kimi auto permission mode is the provider-native no-question setting: normal tool approvals are automatic and `AskUserQuestion` is disabled, but explicit provider hard-deny policies and user-configured deny rules may still block work.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish Kimi headless prompt-mode behavior from Kimi TUI native `--auto` behavior
- **AND THEN** they understand that resumed unattended TUI startup keeps native auto mode

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks what Kimi unattended does
- **THEN** the reference says normal approvals and questions do not prompt the operator
- **AND THEN** it does not claim that Houmao bypasses explicit hard-deny rules

### Requirement: Launch-policy reference excludes Gemini
The launch-policy reference SHALL document no Gemini strategy, version range, owned path, provider hook, unattended behavior, or auth readiness claim.

#### Scenario: Launch-policy inventory omits Gemini
- **WHEN** a reader inspects maintained strategy tables and examples
- **THEN** no Gemini launch-policy entry appears
