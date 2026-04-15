## ADDED Requirements

### Requirement: `houmao-mgr system-skills` supports Copilot homes
`houmao-mgr system-skills install` and `houmao-mgr system-skills status` SHALL accept `copilot` as a supported `--tool` value.

When `--tool copilot` and `--home` is omitted, the command SHALL resolve the effective target home with this precedence:

1. explicit `--home`
2. `COPILOT_HOME`
3. `<cwd>/.github`

For Copilot, the resolved effective home SHALL remain the home root itself, and Houmao-owned installed skills SHALL project under `<effective-home>/skills/`.

The command SHALL NOT add or require a Copilot-specific `--scope` flag.

#### Scenario: Omitted home falls back to the project-scoped Copilot default
- **WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --set user-control` from `/workspace/repo`
- **AND WHEN** no `COPILOT_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command uses `/workspace/repo/.github` as the effective Copilot home
- **AND THEN** the selected skills are installed under `/workspace/repo/.github/skills/`

#### Scenario: Omitted home uses Copilot env redirection first
- **WHEN** `COPILOT_HOME=/tmp/copilot-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --skill houmao-specialist-mgr`
- **THEN** the command installs the selected skill into `/tmp/copilot-home/skills/houmao-specialist-mgr/`
- **AND THEN** it does not redirect that install to the current repository's `.github` directory

#### Scenario: Explicit home supports personal Copilot installs without a scope flag
- **WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --home ~/.copilot --skill houmao-agent-messaging`
- **THEN** the command installs the selected skill into the expanded `~/.copilot/skills/houmao-agent-messaging/` path
- **AND THEN** it does not require a separate `--scope personal` option

#### Scenario: Copilot status reports a project-scoped default home
- **WHEN** an operator runs `houmao-mgr system-skills status --tool copilot` from `/workspace/repo`
- **AND WHEN** no `COPILOT_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command inspects `/workspace/repo/.github` as the effective Copilot home
- **AND THEN** it reports install state for skills under `/workspace/repo/.github/skills/`
