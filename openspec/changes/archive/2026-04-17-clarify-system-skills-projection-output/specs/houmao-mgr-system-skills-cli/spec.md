## ADDED Requirements

### Requirement: `houmao-mgr system-skills install` plain output reports projected skill locations
`houmao-mgr system-skills install` SHALL make the human-readable install result distinguish each selected tool's effective home from the tool-native location where Houmao-owned skills were projected.

For each successful single-tool or multi-tool install, the plain output SHALL report enough projection information for an operator to locate the installed skill files without consulting JSON output or documentation. That projection information SHALL be derived from the installer result for the selected tool, such as the common projection root or the projected relative skill directories.

For Gemini, the plain output SHALL NOT imply that skills were installed directly into the effective home root. When the effective Gemini home is `/workspace/repo`, the plain output SHALL identify `/workspace/repo/.gemini/skills` or home-relative `.gemini/skills/...` paths as the Houmao-owned skill projection location.

The structured install payload SHALL continue to include `home_path`, `projected_relative_dirs`, `resolved_skills`, and `projection_mode` with their existing meanings. Any additional structured fields added for projection roots SHALL be additive.

#### Scenario: Multi-tool install shows Gemini projection root
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,claude,gemini --symlink` from `/workspace/repo`
- **AND WHEN** no `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, or `GEMINI_CLI_HOME` is set
- **THEN** the plain output reports Codex with effective home `/workspace/repo/.codex` and a skill projection location under `/workspace/repo/.codex/skills`
- **AND THEN** the plain output reports Claude with effective home `/workspace/repo/.claude` and a skill projection location under `/workspace/repo/.claude/skills`
- **AND THEN** the plain output reports Gemini with effective home `/workspace/repo` and a skill projection location under `/workspace/repo/.gemini/skills`
- **AND THEN** the plain output does not present `/workspace/repo` alone as the Gemini installed skill location

#### Scenario: Single-tool Gemini install shows projected paths
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --skill houmao-specialist-mgr` from `/workspace/repo`
- **AND WHEN** no `GEMINI_CLI_HOME` is set
- **THEN** the plain output reports the effective home as `/workspace/repo`
- **AND THEN** the plain output reports `.gemini/skills/houmao-specialist-mgr` or `/workspace/repo/.gemini/skills/houmao-specialist-mgr` as the installed skill path

#### Scenario: JSON install output keeps existing fields
- **WHEN** an operator runs `houmao-mgr --print-json system-skills install --tool gemini --skill houmao-specialist-mgr` from `/workspace/repo`
- **THEN** the structured output reports `home_path` as `/workspace/repo`
- **AND THEN** the structured output reports `projected_relative_dirs` containing `.gemini/skills/houmao-specialist-mgr`
- **AND THEN** existing structured fields retain their current meanings

### Requirement: `houmao-mgr system-skills status` plain output reports projected skill paths
`houmao-mgr system-skills status` SHALL make human-readable status output identify the projection path for each discovered Houmao-owned skill, not only the skill name and projection mode.

The command SHALL continue to report the effective home path. For each discovered skill, it SHALL also report the home-relative projected directory or an equivalent absolute projected path.

#### Scenario: Gemini status shows discovered `.gemini/skills` path
- **WHEN** an operator runs `houmao-mgr system-skills status --tool gemini` from `/workspace/repo`
- **AND WHEN** `/workspace/repo/.gemini/skills/houmao-specialist-mgr/SKILL.md` exists
- **THEN** the plain output reports the effective home as `/workspace/repo`
- **AND THEN** the plain output reports `.gemini/skills/houmao-specialist-mgr` or `/workspace/repo/.gemini/skills/houmao-specialist-mgr` for the discovered skill
- **AND THEN** the plain output continues to report the inferred projection mode

### Requirement: `houmao-mgr system-skills uninstall` plain output reports removed projected paths
`houmao-mgr system-skills uninstall` SHALL make human-readable uninstall output identify the projected skill paths it removed or considered absent for each selected tool.

For multi-tool uninstall output, each tool entry SHALL distinguish the effective home from the removed and absent projected skill locations, at least by reporting counts plus the projection root or representative projected relative directories. Gemini output SHALL identify `.gemini/skills` paths rather than implying that current Houmao-owned skills were removed directly from the effective home root.

#### Scenario: Multi-tool uninstall shows Gemini removed projection location
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex,gemini` from `/workspace/repo`
- **AND WHEN** `/workspace/repo/.gemini/skills/houmao-specialist-mgr/SKILL.md` exists before uninstall
- **THEN** the plain output reports Gemini's effective home as `/workspace/repo`
- **AND THEN** the plain output reports `.gemini/skills` or `.gemini/skills/houmao-specialist-mgr` as the removed projection location
- **AND THEN** the plain output does not present `/workspace/repo` alone as the removed Gemini skill location
