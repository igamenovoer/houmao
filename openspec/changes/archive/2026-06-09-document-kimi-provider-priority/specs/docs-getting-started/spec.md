## ADDED Requirements

### Requirement: Getting-started docs prioritize Kimi in provider examples

Getting-started docs SHALL present Kimi Code as a primary supported provider alongside Claude and Codex.

When getting-started docs list all maintained launch-capable providers in neutral prose, they SHALL order them as Claude, Codex, Kimi, then Gemini. When they list only three providers in compact prose, examples, or diagrams, they SHALL list Claude, Codex, and Kimi.

Getting-started docs SHALL continue to document Gemini where the content is describing all supported providers or Gemini-specific behavior, but Gemini SHALL NOT be the default third provider in short examples.

Getting-started docs that introduce Kimi Code SHALL include a Kimi Code 0.11.0 warning that this version does not expose a native system-prompt flag. The warning SHALL tell readers to invoke `houmao-auto-system-prompt` manually before substantive Kimi chat begins when the Houmao system prompt has not been confirmed loaded.

#### Scenario: Architecture overview names Kimi as a primary provider

- **WHEN** a reader opens `docs/getting-started/overview.md`
- **THEN** the opening provider summary includes Kimi Code as a primary provider
- **AND THEN** if Gemini is included in the same neutral provider list, Kimi appears before Gemini

#### Scenario: Quickstart starts from Kimi-aware CLI-agent choices

- **WHEN** a reader opens `docs/getting-started/quickstart.md`
- **THEN** the opening explanation names Claude Code, Codex, and Kimi before Gemini or generic other supported surfaces
- **AND THEN** compact provider examples on the page use Claude, Codex, and Kimi

#### Scenario: Join diagram uses Kimi when only three providers fit

- **WHEN** the quickstart provider TUI adoption diagram lists three provider commands
- **THEN** the diagram lists `claude`, `codex`, and `kimi`
- **AND THEN** Gemini is omitted from that compact diagram unless the diagram is expanded to list all providers

#### Scenario: Quickstart warns about Kimi auto system prompt loading

- **WHEN** a reader opens the Kimi-aware quickstart guidance
- **THEN** the page states that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** it directs Kimi users to invoke `houmao-auto-system-prompt` manually before substantive chat if the prompt is not confirmed loaded
