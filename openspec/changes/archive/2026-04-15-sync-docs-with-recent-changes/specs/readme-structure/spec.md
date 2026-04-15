## MODIFIED Requirements

### Requirement: README What It Is section acknowledges Copilot system-skills target

The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three launch-capable tools (`claude`, `codex`, `gemini`). The mention SHALL use a qualifier that makes clear Copilot is a skill-install surface, not a launch backend.

#### Scenario: Reader understands Copilot scope

- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `gemini` as launch backends and additionally supports `copilot` for system-skill installation
- **AND THEN** they do not conclude that Copilot is a launch backend

### Requirement: README demos section includes writer-team example

The README SHALL include a reference to the `examples/writer-team/` template in or adjacent to the "Runnable Demos" section so that the multi-agent loop example is discoverable alongside the demo scripts.

#### Scenario: Reader finds writer-team in demos area

- **WHEN** a reader scans the "Runnable Demos" section of the README
- **THEN** they find a reference to `examples/writer-team/` with a description of what the example demonstrates
