# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi Code headless live validation guidance

Workbench guidance SHALL describe live/manual validation with a Kimi headless agent prepared through the shared generic fixture flow, while retaining deterministic fake-server E2E as the required automated path. Credential setup SHALL use selected local API references or explicit imported native state outside the checkout rather than a fixed personal fixture path.

#### Scenario: Documentation names Kimi Code headless live lane
- **WHEN** a developer reads the workbench live-validation guidance
- **THEN** it names Kimi headless as the preferred real-agent lane and explains generic fixture preparation with an explicit model and backend case
- **AND THEN** it points native auth setup to local discovery/import when that method is selected
- **AND THEN** it does not require `tests/fixtures/auth-bundles/kimi/personal-a-default/`

#### Scenario: Live validation attaches to existing agent gateway
- **WHEN** a developer connects the workbench to a prepared live Kimi headless agent
- **THEN** the workbench attaches through the existing gateway AG-UI routes
- **AND THEN** GUI lifecycle does not start, stop, restart, shut down, or interrupt that agent
