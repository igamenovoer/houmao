## MODIFIED Requirements

### Requirement: README What It Is section acknowledges Copilot system-skills target
The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three primary launch-capable tools (`claude`, `codex`, `kimi`). The mention SHALL make clear that Copilot is a skill-install surface, not a launch backend.

The README SHALL include a Kimi Code note that identifies 0.34.0 as the minimum supported version and states that support has no upper version limit. It SHALL explain that Houmao applies the complete composed role prompt before provider startup through the managed Kimi home's native `SYSTEM.md`, while preserving Kimi's built-in instructions. It SHALL contain no pre-0.34 compatibility, manual auto-skill invocation, or role-bootstrap guidance.

#### Scenario: Reader understands Copilot scope
- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `kimi` as primary launch backend examples
- **AND THEN** they see that Houmao additionally supports `copilot` for system-skill installation without treating it as a launch backend

#### Scenario: Reader sees current Kimi role-prompt guidance
- **WHEN** a reader scans the README Kimi provider guidance
- **THEN** they see the Kimi 0.34.0 floor, no upper limit, and native managed-home role-prompt behavior
- **AND THEN** they see no pre-0.34 or skill-based prompt-delivery workaround
