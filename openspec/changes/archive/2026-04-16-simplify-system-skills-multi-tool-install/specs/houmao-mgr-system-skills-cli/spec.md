## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
`houmao-mgr system-skills install` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

The supported tool identifiers SHALL include:

- `claude`
- `codex`
- `copilot`
- `gemini`

When `--tool` contains commas, the command SHALL parse the value as an ordered tool list, trimming whitespace around each entry.

The command SHALL reject an empty parsed tool entry, an unsupported tool entry, or a duplicate parsed tool entry before mutating any target home.

The command SHALL accept an optional target home override only when the parsed tool list contains exactly one tool. When the parsed tool list contains more than one tool, the command SHALL reject `--home` before mutating any target home.

When `--home` is omitted, the command SHALL resolve the effective target home for each selected tool with this precedence:

1. tool-native home env var
2. project-scoped default home

For single-tool installs with `--home`, explicit `--home` SHALL take precedence over the tool-native home env var and project-scoped default home.

The tool-native home env vars SHALL be:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Copilot: `COPILOT_HOME`
- Gemini: `GEMINI_CLI_HOME`

The project-scoped default homes SHALL be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Copilot: `<cwd>/.github`
- Gemini: `<cwd>`

For Gemini, the resolved effective home SHALL remain the home root itself, and Houmao-owned installed skills SHALL project under `<effective-home>/.gemini/skills/`.

The command SHALL support these selection inputs:

- repeatable `--skill-set <name>` for named system-skill set selection,
- repeatable `--skill <name>` for explicit current-skill selection.

When neither `--skill-set` nor `--skill` is provided, the command SHALL use the CLI default set list from the packaged catalog.

For multi-tool installs, the command SHALL apply the same selected sets, explicit skills, and resolved projection mode to every selected tool.

The command SHALL NOT expose `--set` or `--default` as part of the supported public install surface.

The command SHALL also support `--symlink` to request symlink projection mode for that explicit install.

If `--symlink` is omitted, the command SHALL use copied projection mode.

If `--symlink` is provided, the command SHALL use the shared Houmao system-skill installer in symlink projection mode and SHALL NOT silently fall back to copied projection.

The command SHALL use the shared Houmao system-skill installer for projection and ownership tracking.

For single-tool installs, the structured result SHALL preserve the existing single-install payload shape with scalar `tool` and `home_path` fields.

For multi-tool installs, the structured result SHALL contain the parsed `tools` list and one single-install-shaped result entry per selected tool.

#### Scenario: Explicit home override wins over tool-native env redirection
- **WHEN** `CODEX_HOME=/tmp/codex-from-env`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-explicit --skill houmao-specialist-mgr`
- **THEN** the command installs the selected skill into `/tmp/codex-explicit`
- **AND THEN** it does not redirect that install to `/tmp/codex-from-env`
- **AND THEN** the structured result uses the existing single-tool payload shape

#### Scenario: Omitted home uses the tool-native env redirect first
- **WHEN** `CLAUDE_CONFIG_DIR=/tmp/claude-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool claude`
- **THEN** the command installs the current Houmao-owned skill list resolved from the CLI default set list into `/tmp/claude-home`
- **AND THEN** it uses copied projection mode unless `--symlink` is supplied

#### Scenario: Omitted home falls back to the project-scoped Codex default
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex` from `/workspace/repo`
- **AND WHEN** no `CODEX_HOME` is set
- **AND WHEN** no `--home`, `--skill-set`, or `--skill` is supplied
- **THEN** the command installs the current Houmao-owned skill list resolved from the CLI default set list into `/workspace/repo/.codex`
- **AND THEN** overlapping set members are deduplicated by first occurrence

#### Scenario: Omitted home uses the project root as the Gemini default home
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --skill-set user-control` from `/workspace/repo`
- **AND WHEN** no `GEMINI_CLI_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command uses `/workspace/repo` as the effective Gemini home
- **AND THEN** the selected skills are installed under `/workspace/repo/.gemini/skills/`

#### Scenario: Install combines named sets and explicit skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --skill-set user-control --skill houmao-agent-email-comms`
- **THEN** the command installs the resolved current Houmao-owned skill list from the named set plus the explicit skill into the explicit target home
- **AND THEN** it does not silently replace that explicit selection with another internal default selection

#### Scenario: Install applies one selected skill in symlink mode
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --skill houmao-specialist-mgr --symlink`
- **THEN** the command installs that selected Houmao-owned skill into the explicit target home using symlink projection mode
- **AND THEN** it does not silently replace that symlink request with copied projection

#### Scenario: Multi-tool install resolves each home independently
- **WHEN** an operator runs `houmao-mgr system-skills install --tool claude,codex,copilot,gemini --skill-set user-control` from `/workspace/repo`
- **AND WHEN** no tool-native home env vars are set
- **AND WHEN** no `--home` is supplied
- **THEN** the command installs the resolved `user-control` skill list into `/workspace/repo/.claude`, `/workspace/repo/.codex`, `/workspace/repo/.github`, and `/workspace/repo`
- **AND THEN** the Gemini selected skills are installed under `/workspace/repo/.gemini/skills/`
- **AND THEN** the structured result contains `tools` and an `installations` entry for each selected tool

#### Scenario: Multi-tool install rejects explicit home override
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,claude --home /tmp/tool-home`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** the error explains that `--home` is only valid when `--tool` names exactly one tool

#### Scenario: Multi-tool install rejects malformed tool lists before mutation
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,,gemini`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** it does not guess a missing tool name or continue with partial selection

#### Scenario: Multi-tool install rejects duplicate tool entries before mutation
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,codex`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** it does not install into the same resolved Codex home twice

#### Scenario: Install fails when a selected set is unknown
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --skill-set unknown-set`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess another named set or continue with partial selection

#### Scenario: Install rejects the removed set flag
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --set user-control`
- **THEN** the command exits non-zero because `--set` is not part of the current command surface
- **AND THEN** the operator must use `--skill-set user-control` for named system-skill set selection

#### Scenario: Install rejects the removed default flag
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --default`
- **THEN** the command exits non-zero because `--default` is not part of the current command surface
- **AND THEN** the operator must omit both `--skill-set` and `--skill` to request CLI-default selection
