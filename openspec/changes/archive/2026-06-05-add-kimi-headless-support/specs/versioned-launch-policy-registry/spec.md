## ADDED Requirements

### Requirement: Registry declares maintained Kimi unattended headless strategy coverage
The launch-policy registry SHALL include maintained Kimi unattended strategy coverage for the `kimi_headless` backend.

That Kimi strategy coverage SHALL remain version-scoped and SHALL declare:

- the compatible Kimi Code CLI version range,
- the minimal input contract needed after provider selection is resolved,
- evidence provenance from local source analysis and live prompt-mode probes,
- the Kimi startup surfaces Houmao owns for unattended prompt-mode launch, and
- the ordered actions or validation needed before Kimi provider start.

The Kimi strategy metadata SHALL separate credential readiness from unattended startup compatibility and SHALL describe Kimi's maintained auth readiness in terms of projected OAuth config/token storage or Kimi env-model variables.

#### Scenario: Maintainer inspects Kimi unattended strategy metadata
- **WHEN** a maintainer inspects the launch-policy registry entry that covers maintained Kimi unattended startup
- **THEN** the entry declares `kimi_headless` as a supported backend
- **AND THEN** it declares the compatible Kimi version range, evidence basis, owned startup surfaces, and ordered actions or validation
- **AND THEN** it keeps credential readiness distinct from the unattended startup ownership model

#### Scenario: Kimi strategy rejects prompt-mode-incompatible launch args
- **WHEN** the runtime resolves a compatible Kimi unattended strategy
- **AND WHEN** caller launch args include Kimi prompt-mode-incompatible startup flags such as `--auto`, `--yolo`, or `--plan`
- **THEN** the strategy rejects or removes the conflicting launch args before provider start according to its declared action contract
- **AND THEN** the final Kimi prompt-mode command remains valid for unattended headless execution

#### Scenario: Unknown Kimi version does not silently use maintained strategy
- **WHEN** a Kimi unattended launch requests a Kimi Code CLI version outside the declared compatible strategy range
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails explicitly instead of silently using a best-effort Kimi strategy
