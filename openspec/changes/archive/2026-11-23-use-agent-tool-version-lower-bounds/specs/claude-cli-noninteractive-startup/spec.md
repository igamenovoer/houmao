# Spec Delta

## MODIFIED Requirements

### Requirement: Orchestrated Claude launch is non-interactive

The system SHALL support an unattended startup path for orchestrated Claude Code launches that prevents startup from blocking on dangerous-mode prompts, API-key approval prompts, workspace trust dialogs, onboarding, or equivalent operator confirmation surfaces.

When that unattended path is requested, the system SHALL detect the actual Claude Code version, resolve a compatible Claude launch policy strategy from the maintained Claude registry, and apply that strategy before starting Claude Code.

For each maintained unattended backend, the Claude registry SHALL declare an inclusive minimum that admits eligible later releases. The maintained unattended floor SHALL track the qualified tracked-TUI floor, currently `>=2.1.296`. Strategies qualified against older releases SHALL be realigned or removed when the floor moves.

The unattended contract SHALL be validated against the current default permission behavior of the floor version. Claude 2.1.296 defaults to auto permission mode and renders the workspace trust dialog even under `--dangerously-skip-permissions` for an untrusted workdir. Trust seeding and startup-prompt assumptions SHALL be re-probed live whenever the floor moves.

#### Scenario: Compatible Claude strategy prevents up-front operator prompts

- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected Claude Code version matches a compatible strategy
- **THEN** the system applies the selected Claude launch strategy before starting Claude Code
- **AND THEN** Claude Code startup does not block on up-front API-key approval, trust, dangerous-mode, or onboarding prompts

#### Scenario: Maintained unattended Claude path has declared strategy coverage

- **WHEN** `raw_launch` or `claude_headless` is selected with an eligible Claude Code release at or above the floor
- **THEN** the declared minimum matches that version and backend

#### Scenario: Unsupported Claude version fails unattended launch before process start

- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version under the declared minimums
- **THEN** the system fails the launch before starting Claude Code
- **AND THEN** the error identifies the detected Claude Code version, unattended policy request, and requested backend surface
