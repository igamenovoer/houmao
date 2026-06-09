## ADDED Requirements

### Requirement: System-skills overview uses Kimi-priority install examples

The system-skills overview guide SHALL use Kimi-priority ordering in provider/tool installation examples and prose.

When the guide lists all system-skill installation targets, launch-capable providers SHALL appear as Claude, Codex, Kimi, then Gemini, followed by Copilot as the skill-install-only target unless the surrounding text specifically discusses Copilot.

When the guide shows a short three-tool launch-provider install example, it SHALL use `claude,codex,kimi`.

When the guide discusses Kimi skill reachability, it SHALL warn that Kimi Code 0.11.0 does not expose a native system-prompt flag. The warning SHALL state that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins when automatic skill startup has not loaded the Houmao system prompt.

#### Scenario: Overview install command places Kimi before Gemini

- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** multi-tool install examples that include Gemini also include Kimi before Gemini
- **AND THEN** Copilot is only included when the example is about system-skill installation targets

#### Scenario: Overview explains Kimi projection without demoting it

- **WHEN** the guide explains tool-home resolution or projection caveats
- **THEN** Kimi projection and discovery caveats remain documented
- **AND THEN** those caveats do not make Gemini appear as the primary third launch provider

#### Scenario: Overview warns about Kimi auto system prompt loading

- **WHEN** a reader reviews Kimi system-skill reachability guidance
- **THEN** the guide states that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** it tells readers that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins
