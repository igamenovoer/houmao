## MODIFIED Requirements

### Requirement: System-skills reference documents effective-home resolution and omitted-selection defaults
The CLI reference pages `docs/reference/cli/system-skills.md` and `docs/reference/cli/houmao-mgr.md` SHALL describe `houmao-mgr system-skills install` as requiring `--tool` with either one supported tool identifier or a comma-separated list of supported tool identifiers.

The CLI reference pages `docs/reference/cli/system-skills.md` and `docs/reference/cli/houmao-mgr.md` SHALL describe `houmao-mgr system-skills status` as requiring one supported `--tool` value.

That coverage SHALL describe `--home` as optional for single-tool `install` and `status` invocations.

That coverage SHALL state that `--home` is invalid for `system-skills install` when `--tool` names more than one comma-separated tool.

That coverage SHALL document `--skill-set <name>` as the repeatable named system-skill set selection flag for `system-skills install`.

That coverage SHALL state that `--set` is no longer part of the supported public `system-skills install` surface.

That coverage SHALL document effective-home resolution for omitted-home installs and status inspection with this precedence:

1. tool-native home env var
2. project-scoped default home

That coverage SHALL document explicit `--home` as taking precedence over tool-native home env vars and project-scoped defaults for single-tool commands.

That coverage SHALL document the tool-native home env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Copilot: `COPILOT_HOME`
- Gemini: `GEMINI_CLI_HOME`

That coverage SHALL document the project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Copilot: `<cwd>/.github`
- Gemini: `<cwd>`

That coverage SHALL state that omitting both `--skill-set` and `--skill` resolves the packaged CLI-default set list.

That coverage SHALL NOT present `--default` as part of the current public `system-skills install` surface.

That coverage SHALL explain that the default Gemini home root is `<cwd>`, which yields Houmao-owned skill projection under `<cwd>/.gemini/skills/`.

That coverage SHALL show at least one comma-separated multi-tool install example and at least one single-tool explicit-home install example.

That coverage SHALL show at least one named-set install example using `--skill-set`.

That coverage SHALL explain that single-tool JSON output keeps the scalar install payload shape and multi-tool JSON output wraps per-tool install results under an aggregate payload.

#### Scenario: Reader sees the effective-home precedence in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents `--home` as optional for single-tool `install` and `status`
- **AND THEN** it explains the precedence order of explicit `--home`, tool-native env redirection, and project-scoped default home for single-tool commands

#### Scenario: Reader sees comma-separated multi-tool install syntax
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents that `system-skills install --tool` accepts comma-separated supported tools
- **AND THEN** it shows an example such as `houmao-mgr system-skills install --tool claude,codex,copilot,gemini`

#### Scenario: Reader sees explicit skill-set flag naming
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents `--skill-set <name>` as the named system-skill set selection flag
- **AND THEN** the page does not present `--set` as the current named-set selection flag

#### Scenario: Reader sees the multi-tool home restriction
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that `--home` cannot be combined with comma-separated multi-tool install
- **AND THEN** it explains that operators who need explicit homes must run separate single-tool install commands

#### Scenario: Reader understands single-tool and multi-tool install output
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that existing single-tool JSON output keeps scalar `tool` and `home_path` fields
- **AND THEN** it explains that multi-tool JSON output reports `tools` plus one per-tool installation result

#### Scenario: Reader sees the Gemini project-root default home clearly
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that Gemini defaults to `<cwd>` rather than `<cwd>/.gemini`
- **AND THEN** it explains that omitted-home Gemini installs project skills under `<cwd>/.gemini/skills/`

#### Scenario: Reader does not see the removed default flag in current reference docs
- **WHEN** a reader opens `docs/reference/cli/system-skills.md` or `docs/reference/cli/houmao-mgr.md`
- **THEN** the current command shape does not present `--set` or `--default` as a supported `system-skills install` option
- **AND THEN** the reference explains that omitting both `--skill-set` and `--skill` is the supported way to request CLI-default selection
