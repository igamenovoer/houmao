## ADDED Requirements

### Requirement: System-skills reference documents Copilot support
The CLI reference page `docs/reference/cli/system-skills.md` SHALL document Copilot as a supported explicit `system-skills install|status --tool` target.

That page SHALL document:

- Copilot's tool-native home env var as `COPILOT_HOME`,
- Copilot's project-scoped default home as `<cwd>/.github`,
- Copilot's visible projection root as `skills/`, yielding `.github/skills/<houmao-skill>/` for omitted-home project installs,
- explicit personal Copilot installs through `--home ~/.copilot`, yielding `~/.copilot/skills/<houmao-skill>/`,
- that no `--scope` flag is required or supported for Copilot system-skill installation.

#### Scenario: Reader sees Copilot in system-skills home resolution
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page lists Copilot alongside Claude, Codex, and Gemini in the supported tool-home resolution coverage
- **AND THEN** it identifies `COPILOT_HOME` and `<cwd>/.github` as Copilot's env and project-default home inputs

#### Scenario: Reader understands Copilot projection paths
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that Copilot skills project under `skills/<houmao-skill>/` relative to the resolved Copilot home
- **AND THEN** it gives examples for both `.github/skills/<houmao-skill>/` and `~/.copilot/skills/<houmao-skill>/`
