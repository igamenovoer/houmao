## ADDED Requirements

### Requirement: CLI references use Kimi-priority provider lists

CLI reference pages SHALL use Kimi-priority ordering when documenting provider and tool lists.

When a CLI reference page lists launch-capable providers in neutral prose or examples, it SHALL order them as Claude, Codex, Kimi, then Gemini. When it lists only three launch-capable providers, it SHALL list Claude, Codex, and Kimi.

When a CLI reference page lists system-skill installation targets, it SHALL keep Copilot scoped to skill installation. In such lists, launch-capable providers SHALL appear before Copilot in Kimi-priority order unless the page is specifically describing Copilot.

#### Scenario: system-skills command summary includes Kimi ahead of Gemini

- **WHEN** a reader opens `docs/reference/cli.md`, `docs/reference/cli/houmao-mgr.md`, or `docs/reference/cli/system-skills.md`
- **THEN** system-skill installation target lists include Kimi
- **AND THEN** Kimi appears before Gemini in those lists
- **AND THEN** Copilot is presented as a system-skill installation target rather than a launch backend

#### Scenario: CLI examples use Kimi as the third short provider

- **WHEN** a CLI reference example lists a short comma-separated provider/tool set
- **THEN** the example uses `claude,codex,kimi` when it is demonstrating three launch-capable providers
- **AND THEN** Gemini appears only in examples that list all maintained launch-capable providers or explain Gemini-specific behavior

#### Scenario: Credential references keep Kimi visible

- **WHEN** a reader opens project or internals credential CLI reference coverage
- **THEN** supported credential CRUD lanes list Kimi before Gemini
- **AND THEN** login-helper caveats still state accurately that helper workflows are maintained for Claude, Codex, and Gemini while Kimi uses explicit CRUD inputs
