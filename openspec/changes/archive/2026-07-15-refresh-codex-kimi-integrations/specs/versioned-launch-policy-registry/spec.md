## MODIFIED Requirements

### Requirement: Registry declares maintained Kimi unattended strategy coverage
The launch-policy registry SHALL include maintained Kimi 0.23.x unattended strategy coverage for the `kimi_headless` backend and for the `raw_launch` backend used by Kimi Code local-interactive TUI launch.

That Kimi strategy coverage SHALL remain version-scoped and SHALL declare:

- the compatible Kimi Code CLI version range,
- the minimal input contract needed after provider selection is resolved,
- evidence provenance from current local source analysis and live prompt-mode or TUI probes,
- the Kimi startup surfaces Houmao owns for unattended prompt-mode launch and unattended TUI launch,
- any runtime-home config keys Houmao owns, and
- the ordered actions or validation needed before Kimi provider start.

For `kimi_headless`, maintained coverage SHALL avoid prompt-mode-incompatible startup flags such as `--auto`, `--yolo`, and `--plan`. Kimi prompt mode's native approval and question handlers SHALL provide the unattended posture.

For `raw_launch`, maintained unattended coverage SHALL add native `--auto` to the final Kimi TUI startup command for both fresh and resumed sessions. It SHALL NOT submit `/auto on` or another conversational command to establish launch policy. The strategy MAY also set `default_permission_mode = "auto"` as inspectable fallback state, but the final CLI argument SHALL define the startup authority.

The Kimi strategy metadata SHALL separate credential readiness from unattended startup compatibility and SHALL describe Kimi's maintained auth readiness in terms of projected OAuth config/token storage or Kimi env-model variables.

#### Scenario: Maintainer inspects Kimi headless unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi headless strategy
- **THEN** the entry declares `kimi_headless`, the Kimi 0.23.x range, evidence, owned startup surfaces, and validation
- **AND THEN** credential readiness remains distinct from unattended startup ownership

#### Scenario: Maintainer inspects Kimi TUI unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi local-interactive unattended strategy
- **THEN** the entry declares `raw_launch` and native `--auto` ownership
- **AND THEN** it declares no runtime `/auto on` bootstrap action

#### Scenario: Kimi headless strategy rejects prompt-mode-incompatible launch args
- **WHEN** a compatible Kimi headless unattended strategy receives caller arguments containing `--auto`, `--yolo`, or `--plan`
- **THEN** the strategy rejects or removes those arguments before provider start
- **AND THEN** the final `-p` command remains valid and unattended

#### Scenario: Kimi resumed TUI keeps native auto mode
- **WHEN** a compatible unattended Kimi TUI launch resumes through `--continue` or `--session <session_id>`
- **THEN** the final provider command also contains `--auto`
- **AND THEN** Houmao does not send a policy-changing chat command after readiness

#### Scenario: Unknown Kimi version does not silently use maintained strategy
- **WHEN** a Kimi unattended launch requests a version outside the declared compatible strategy range
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails explicitly

