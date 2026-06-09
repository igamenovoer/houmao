## MODIFIED Requirements

### Requirement: Registry declares maintained Kimi unattended strategy coverage
The launch-policy registry SHALL include maintained Kimi unattended strategy coverage for the `kimi_headless` backend and for the `raw_launch` backend used by Kimi Code local-interactive TUI launch.

That Kimi strategy coverage SHALL remain version-scoped and SHALL declare:

- the compatible Kimi Code CLI version range,
- the minimal input contract needed after provider selection is resolved,
- evidence provenance from local source analysis and live prompt-mode or TUI probes,
- the Kimi startup surfaces Houmao owns for unattended prompt-mode launch and unattended TUI launch,
- any runtime-home config keys Houmao owns for Kimi unattended TUI launch, and
- the ordered actions or validation needed before Kimi provider start.

For `kimi_headless`, maintained Kimi unattended strategy coverage SHALL continue to avoid prompt-mode-incompatible startup flags such as `--auto`, `--yolo`, and `--plan`.

For `raw_launch`, maintained Kimi unattended strategy coverage SHALL force Kimi Code `default_permission_mode` to `auto` in the managed runtime home before provider start and SHALL NOT rely on adding `--auto` to the final Kimi TUI startup command.

The Kimi strategy metadata SHALL separate credential readiness from unattended startup compatibility and SHALL describe Kimi's maintained auth readiness in terms of projected OAuth config/token storage or Kimi env-model variables.

#### Scenario: Maintainer inspects Kimi headless unattended strategy metadata
- **WHEN** a maintainer inspects the launch-policy registry entry that covers maintained Kimi headless unattended startup
- **THEN** the entry declares `kimi_headless` as a supported backend
- **AND THEN** it declares the compatible Kimi version range, evidence basis, owned startup surfaces, and ordered actions or validation
- **AND THEN** it keeps credential readiness distinct from the unattended startup ownership model

#### Scenario: Maintainer inspects Kimi TUI unattended strategy metadata
- **WHEN** a maintainer inspects the launch-policy registry entry that covers maintained Kimi local-interactive unattended startup
- **THEN** the entry declares `raw_launch` as a supported backend
- **AND THEN** it declares Kimi `default_permission_mode = auto` as strategy-owned runtime-home state
- **AND THEN** it does not declare `--auto` as a required final TUI startup argument

#### Scenario: Kimi headless strategy rejects prompt-mode-incompatible launch args
- **WHEN** the runtime resolves a compatible Kimi headless unattended strategy
- **AND WHEN** caller launch args include Kimi prompt-mode-incompatible startup flags such as `--auto`, `--yolo`, or `--plan`
- **THEN** the strategy rejects or removes the conflicting launch args before provider start according to its declared action contract
- **AND THEN** the final Kimi prompt-mode command remains valid for unattended headless execution

#### Scenario: Kimi TUI strategy owns automatic permission config
- **WHEN** the runtime resolves a compatible Kimi raw-launch unattended strategy
- **AND WHEN** the managed Kimi runtime-home `config.toml` omits `default_permission_mode` or sets it to `manual` or `yolo`
- **THEN** the strategy writes `default_permission_mode = "auto"` before provider start
- **AND THEN** unrelated Kimi provider, model, OAuth, skill, and telemetry config remains intact

#### Scenario: Unknown Kimi version does not silently use maintained strategy
- **WHEN** a Kimi unattended launch requests a Kimi Code CLI version outside the declared compatible strategy range
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails explicitly instead of silently using a best-effort Kimi strategy
