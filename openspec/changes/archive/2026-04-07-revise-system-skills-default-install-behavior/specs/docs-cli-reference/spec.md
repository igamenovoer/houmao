## ADDED Requirements

### Requirement: System-skills reference documents effective-home resolution and omitted-selection defaults
The CLI reference pages `docs/reference/cli/system-skills.md` and `docs/reference/cli/houmao-mgr.md` SHALL describe `houmao-mgr system-skills install` and `houmao-mgr system-skills status` as requiring `--tool` and accepting an optional `--home`.

That coverage SHALL document effective-home resolution with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

That coverage SHALL document the tool-native home env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Gemini: `GEMINI_CLI_HOME`

That coverage SHALL document the project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

That coverage SHALL state that omitting both `--set` and `--skill` resolves the packaged CLI-default set list.

That coverage SHALL NOT present `--default` as part of the current public `system-skills install` surface.

That coverage SHALL explain that the default Gemini home root is `<cwd>`, which yields Houmao-owned skill projection under `<cwd>/.agents/skills/`.

#### Scenario: Reader sees the effective-home precedence in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents `--home` as optional for `install` and `status`
- **AND THEN** it explains the precedence order of explicit `--home`, tool-native env redirection, and project-scoped default home

#### Scenario: Reader sees the Gemini project-root default home clearly
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that Gemini defaults to `<cwd>` rather than `<cwd>/.gemini`
- **AND THEN** it explains that omitted-home Gemini installs project skills under `<cwd>/.agents/skills/`

#### Scenario: Reader does not see the removed default flag in current reference docs
- **WHEN** a reader opens `docs/reference/cli/system-skills.md` or `docs/reference/cli/houmao-mgr.md`
- **THEN** the current command shape does not present `--default` as a supported `system-skills install` option
- **AND THEN** the reference explains that omitting both `--set` and `--skill` is the supported way to request CLI-default selection
