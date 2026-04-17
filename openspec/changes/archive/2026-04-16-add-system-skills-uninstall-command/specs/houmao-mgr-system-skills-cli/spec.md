## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` exposes the current Houmao-owned skill installation surface
`houmao-mgr` SHALL expose a top-level `system-skills` command family for the current Houmao-owned system-skill set.

At minimum, that command family SHALL include:

- `list`
- `install`
- `status`
- `uninstall`

#### Scenario: Help shows the system-skill command family
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** the help output lists `list`, `install`, `status`, and `uninstall`
- **AND THEN** the command family is presented as the Houmao-owned system-skill installation surface for the current skill set

## ADDED Requirements

### Requirement: `houmao-mgr system-skills uninstall` removes all known Houmao-owned skills from resolved homes
`houmao-mgr system-skills uninstall` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

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

For single-tool uninstalls with `--home`, explicit `--home` SHALL take precedence over the tool-native home env var and project-scoped default home.

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

For Gemini, the resolved effective home SHALL remain the home root itself, and Houmao-owned skills SHALL be removed from `<effective-home>/.gemini/skills/`.

The command SHALL NOT accept `--skill`, `--skill-set`, `--set`, `--default`, `--symlink`, or another selection flag. Uninstall SHALL always target every current Houmao-owned skill name in the packaged catalog.

For each current catalog-known Houmao-owned skill, the command SHALL compute the exact current tool-native destination path and remove that path when it exists as a directory, file, or symlink.

The command SHALL NOT remove parent skill roots, unrelated tool-home content, unrecognized `houmao-*` paths, legacy family-namespaced paths, or obsolete install-state files.

The command SHALL be idempotent. Missing current Houmao-owned skill paths SHALL be reported as absent or skipped rather than treated as failures.

The command SHALL NOT create a missing resolved target home, parent skill root, or skill directory just to perform uninstall.

For single-tool uninstalls, the structured result SHALL use a single-uninstall payload with scalar `tool` and `home_path` fields.

For multi-tool uninstalls, the structured result SHALL contain the parsed `tools` list and one single-uninstall-shaped result entry per selected tool.

At minimum, each single-tool uninstall result SHALL report removed skill names, removed projected relative dirs, absent skill names, and absent projected relative dirs.

#### Scenario: Single-tool uninstall removes current copied and symlinked skill paths
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/codex-home`
- **AND WHEN** `/tmp/codex-home` contains current Houmao-owned skill paths as copied directories, symlinks, or files under `skills/`
- **THEN** the command removes those current catalog-known Houmao skill paths
- **AND THEN** the structured result reports the removed skill names and projected relative dirs

#### Scenario: Uninstall leaves unrelated content in place
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/codex-home`
- **AND WHEN** `/tmp/codex-home` contains `skills/custom-user-skill/`, legacy family-namespaced paths, parent skill roots, or obsolete `.houmao/system-skills/install-state.json`
- **THEN** the command leaves those paths in place
- **AND THEN** it removes only exact current catalog-known Houmao system-skill projection paths

#### Scenario: Uninstall is idempotent for missing skill paths
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool claude --home /tmp/claude-home`
- **AND WHEN** some current Houmao-owned skill projection paths are missing
- **THEN** the command succeeds
- **AND THEN** the structured result reports the missing current skill paths as absent or skipped

#### Scenario: Uninstall does not create a missing home
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/missing-codex-home`
- **AND WHEN** `/tmp/missing-codex-home` does not exist
- **THEN** the command succeeds without creating `/tmp/missing-codex-home`
- **AND THEN** the structured result reports current catalog-known Houmao skills as absent

#### Scenario: Uninstall uses tool-native env redirection when home is omitted
- **WHEN** `CODEX_HOME=/tmp/codex-from-env`
- **AND WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex`
- **THEN** the command uses `/tmp/codex-from-env` as the effective target home
- **AND THEN** it removes current catalog-known Houmao system-skill projection paths from that home

#### Scenario: Uninstall supports comma-separated multi-tool homes
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool claude,codex,copilot,gemini` from `/workspace/repo`
- **AND WHEN** no tool-native home env vars are set
- **AND WHEN** no `--home` is supplied
- **THEN** the command resolves `/workspace/repo/.claude`, `/workspace/repo/.codex`, `/workspace/repo/.github`, and `/workspace/repo` as the target homes
- **AND THEN** the Gemini current skill paths are removed from `/workspace/repo/.gemini/skills/`
- **AND THEN** the structured result contains `tools` and an `uninstallations` entry for each selected tool

#### Scenario: Multi-tool uninstall rejects explicit home override
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex,claude --home /tmp/tool-home`
- **THEN** the command fails explicitly before removing any skill path
- **AND THEN** the error explains that `--home` is only valid when `--tool` names exactly one tool

#### Scenario: Uninstall rejects install-only selection flags
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --skill houmao-specialist-mgr`
- **THEN** the command exits non-zero because selection flags are not part of the uninstall surface
- **AND THEN** the operator must omit selection flags to remove all current known Houmao system skills for that home

#### Scenario: Status after uninstall reports no current installed Houmao-owned skills
- **WHEN** an operator uninstalls Houmao system skills from a Codex home
- **AND WHEN** the operator later runs `houmao-mgr system-skills status --tool codex --home <that-home>`
- **THEN** status reports no installed current Houmao-owned skills for that home
