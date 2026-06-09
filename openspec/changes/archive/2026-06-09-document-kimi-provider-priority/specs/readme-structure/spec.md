## MODIFIED Requirements

### Requirement: README What It Is section acknowledges Copilot system-skills target

The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three primary launch-capable tools (`claude`, `codex`, `kimi`). The mention SHALL use a qualifier that makes clear Copilot is a skill-install surface, not a launch backend.

When the README opening paragraph or nearby first-screen prose mentions all maintained launch-capable providers, it SHALL order them as `claude`, `codex`, `kimi`, then `gemini`.

#### Scenario: Reader understands Copilot scope

- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `kimi` as the primary launch backend examples
- **AND THEN** they see Gemini only after Kimi when a complete launch-provider list appears
- **AND THEN** they see that Houmao additionally supports `copilot` for system-skill installation
- **AND THEN** they do not conclude that Copilot is a launch backend

## ADDED Requirements

### Requirement: README provider examples prioritize Kimi over Gemini

The README SHALL use Kimi-priority provider ordering in launch-provider examples and diagrams.

When a README sentence, command example, or diagram lists only three launch-capable providers, it SHALL list Claude, Codex, and Kimi rather than Gemini as the third provider.

When a README sentence, command example, or diagram lists all maintained launch-capable providers, it SHALL order them as Claude, Codex, Kimi, then Gemini.

README system-skill installation examples MAY include Copilot when the context is explicitly about skill-install targets, but Copilot SHALL remain outside launch-provider examples.

The README SHALL include a Kimi Code warning that names Kimi Code 0.11.0 and states that this version does not expose a native system-prompt flag. The warning SHALL tell readers that Kimi Code users may need to invoke `houmao-auto-system-prompt` manually before substantive chat begins when the Houmao system prompt is not confirmed loaded.

#### Scenario: Architecture diagram uses Kimi as the third provider

- **WHEN** a reader views the README Architecture at a Glance diagram
- **THEN** the three visible provider examples include Claude, Codex, and Kimi
- **AND THEN** Gemini does not appear as the third provider in that compact diagram

#### Scenario: README provider-mix example uses Kimi priority

- **WHEN** a reader scans README use cases or quick provider examples
- **THEN** compact examples mention Claude, Codex, and Kimi
- **AND THEN** complete provider lists place Kimi before Gemini

#### Scenario: README skill-install examples keep Copilot scoped

- **WHEN** a README command example includes Copilot
- **THEN** the surrounding text identifies the example as system-skill installation or projection
- **AND THEN** the README does not present Copilot as a managed launch backend

#### Scenario: README warns about Kimi system-prompt support

- **WHEN** a reader scans the README Kimi provider guidance
- **THEN** they see that Kimi Code 0.11.0 does not expose a native system-prompt flag
- **AND THEN** they see that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins
