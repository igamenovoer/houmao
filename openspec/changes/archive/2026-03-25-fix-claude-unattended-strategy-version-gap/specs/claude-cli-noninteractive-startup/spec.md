## MODIFIED Requirements

### Requirement: Orchestrated Claude launch is non-interactive
The system SHALL support an unattended startup path for orchestrated Claude Code launches that prevents startup from blocking on dangerous-mode prompts, API-key approval prompts, workspace trust dialogs, onboarding, or equivalent operator confirmation surfaces.

When that unattended path is requested, the system SHALL detect the actual Claude Code version, resolve a compatible Claude launch policy strategy from the maintained Claude registry, and apply that strategy before starting Claude Code.

For each Claude version/backend pair that the repository intentionally maintains as a supported unattended launch path, the Claude unattended registry SHALL contain at least one compatible strategy entry whose declared supported-version range covers that pair.

Those supported-version declarations SHALL use one dependency-style range expression per strategy entry (for example `>=2.1.81,<2.2`) so maintained compatibility is explicit and readable without depending on strategy ids or nearest-lower fallback.

#### Scenario: Compatible Claude strategy prevents up-front operator prompts
- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected Claude Code version matches a compatible strategy
- **THEN** the system applies the selected Claude launch strategy before starting Claude Code
- **AND THEN** Claude Code startup does not block on up-front API-key approval, trust, dangerous-mode, or onboarding prompts

#### Scenario: Maintained unattended Claude path has declared strategy coverage
- **WHEN** the repository maintains unattended Claude launch on backend surface `raw_launch` or `claude_headless`
- **AND WHEN** a Claude version is declared supported for that maintained path
- **THEN** the Claude unattended registry contains at least one strategy entry whose declared supported-version range matches that version/backend pair
- **AND THEN** unattended launch on that maintained path does not depend on undocumented version drift assumptions

#### Scenario: Unsupported Claude version fails unattended launch before process start
- **WHEN** an orchestrated Claude launch requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version under the declared supported-version ranges
- **THEN** the system fails the launch before starting Claude Code
- **AND THEN** the error identifies the detected Claude Code version, unattended policy request, and requested backend surface

## ADDED Requirements

### Requirement: Claude unattended compatibility drift is covered for maintained launch paths
The repository SHALL include coverage that validates strategy compatibility for the maintained unattended Claude launch paths used by runtime-managed workflows.

#### Scenario: Coverage detects missing strategy support for a maintained Claude path
- **WHEN** the maintained Claude unattended compatibility coverage runs
- **AND WHEN** no registered Claude strategy's declared supported-version range matches the expected version/backend pair for that maintained path
- **THEN** the coverage fails
- **AND THEN** the failure identifies the missing Claude version/backend coverage gap
