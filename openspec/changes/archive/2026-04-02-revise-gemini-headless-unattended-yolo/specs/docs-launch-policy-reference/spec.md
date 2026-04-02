## MODIFIED Requirements

### Requirement: Launch policy reference page exists

The build-phase reference SHALL include a page at `docs/reference/build-phase/launch-policy.md` documenting the launch policy engine. The page SHALL explain:

- What a launch policy is: a set of rules that govern agent behavior during the run phase, including operator prompt mode, auto-approval settings, and provider-specific constraints.
- The `OperatorPromptMode` enum: the available prompt modes and what each means for agent autonomy and operator involvement.
- Provider hooks: how launch policies can include provider-specific hooks that customize behavior for Claude, Codex, or Gemini backends, including strategy-owned startup surfaces such as Gemini unattended approval mode and sandbox posture.
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
