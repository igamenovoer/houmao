## ADDED Requirements

### Requirement: `houmao-mgr system-skills` rejects the removed LLM Wiki selector
The `houmao-mgr system-skills` command family SHALL treat `houmao-utils-llm-wiki` as an unknown system skill rather than as a current or retired Houmao-owned skill.

The command family SHALL NOT report stale `houmao-utils-llm-wiki` projection paths as current installed skills or retired leftovers.

#### Scenario: Explicit install of removed skill fails
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill houmao-utils-llm-wiki`
- **THEN** the command fails before mutating the target home
- **AND THEN** the error identifies `houmao-utils-llm-wiki` as an unknown system skill

#### Scenario: Status ignores stale removed skill path
- **WHEN** a Codex home contains `skills/houmao-utils-llm-wiki/`
- **AND WHEN** an operator runs `houmao-mgr system-skills status --tool codex --home <home>`
- **THEN** the command does not report `houmao-utils-llm-wiki` as an installed current skill
- **AND THEN** the command does not report `houmao-utils-llm-wiki` as a retired leftover

## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` surfaces utility skills through all
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned utility skills.

That current inventory SHALL surface `houmao-utils-workspace-mgr` as an installable packaged utility skill.

The reported named sets SHALL include `all` as the set that contains current utility skills and SHALL NOT report `utils` as a current installable set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-utils-workspace-mgr`.

#### Scenario: List reports current utility skills and all
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-utils-workspace-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-utils-llm-wiki` in the current Houmao-owned skill inventory
- **AND THEN** it reports `all` as the named set that includes current utility skills
- **AND THEN** it does not report `utils` as a current named set

#### Scenario: Omitted-selection install and status report current utility skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the install result reports `houmao-utils-workspace-mgr` in the resolved current skill list
- **AND THEN** it does not report `houmao-utils-llm-wiki` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-utils-workspace-mgr` as installed when the CLI-default install completed successfully

## REMOVED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the LLM Wiki utility skill and utils set
**Reason**: `houmao-utils-llm-wiki` and the previous explicit `utils` install surface are no longer supported as current Houmao system-skill inventory.

**Migration**: Use currently listed system skills. Remove stale `houmao-utils-llm-wiki` copies or symlinks manually if desired.
