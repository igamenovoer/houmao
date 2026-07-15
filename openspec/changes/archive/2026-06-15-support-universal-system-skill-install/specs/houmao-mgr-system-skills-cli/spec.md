## ADDED Requirements

### Requirement: `houmao-mgr system-skills` supports the universal install target
`houmao-mgr system-skills install`, `houmao-mgr system-skills uninstall`, and `houmao-mgr system-skills status` SHALL accept `universal` as a supported system-skill target through `--tool`.

When `--tool universal` is used without `--home`, the command SHALL resolve the effective home to the real OS user's `~/.agents` directory and project Houmao-owned skills under `skills/`.

When `--tool universal --home <path>` is used, `<path>` SHALL be interpreted as the universal home root that contains the `skills/` directory, not as the skill root itself.

For comma-separated install and uninstall selectors, `universal` SHALL participate like other supported targets and SHALL use its own omitted-home resolution when `--home` is not supplied.

Structured output SHALL report `"tool": "universal"`, the resolved universal home path, and projected relative directories under `skills/`.

Plain output SHALL distinguish the universal home from the projected skill root so operators can see the concrete `~/.agents/skills` target.

#### Scenario: Omitted-home universal install uses user agents home
- **WHEN** an operator runs `houmao-mgr system-skills install --tool universal --skill houmao-agent-definition` with HOME set to `/home/alice`
- **THEN** the command installs the selected skill under `/home/alice/.agents/skills/houmao-agent-definition/`
- **AND THEN** structured output reports the home path `/home/alice/.agents`
- **AND THEN** structured output reports projected relative directory `skills/houmao-agent-definition`

#### Scenario: Explicit universal home is a root containing skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool universal --home /tmp/shared-agents --skill houmao-agent-definition`
- **THEN** the command installs the selected skill under `/tmp/shared-agents/skills/houmao-agent-definition/`
- **AND THEN** plain output identifies `/tmp/shared-agents/skills` as the skill root

#### Scenario: Multi-target install includes universal
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,universal --skill-set core` without `--home`
- **THEN** the command installs the core selection into the resolved Codex home
- **AND THEN** the command installs the same core selection into the resolved universal home under `skills/`

#### Scenario: Universal status and uninstall use the same target
- **WHEN** an operator has installed Houmao-owned skills with `--tool universal`
- **THEN** `houmao-mgr system-skills status --tool universal` reports those installed skills from the resolved universal home
- **AND THEN** `houmao-mgr system-skills uninstall --tool universal` removes current and retired Houmao-owned projections from that same universal home

### Requirement: `houmao-mgr system-skills` names Kimi Code CLI with the `kimi` target
`houmao-mgr system-skills` help and documentation SHALL define the `kimi` target as Kimi Code CLI.

The command SHALL NOT accept `kimi-code` as an alias for `kimi`.

When an operator selects `kimi-code`, the command SHALL fail before filesystem mutation and SHALL direct the operator to use `kimi` for Kimi Code CLI.

Help text and documentation SHALL warn that the `kimi` target is not for the legacy MoonshotAI `kimi-cli` project, which upstream says is being wound down in favor of Kimi Code CLI.

Kimi-specific output or docs SHALL NOT claim that `$KIMI_CODE_HOME/skills` is never discovered by Kimi Code. They SHALL instead explain that `--home` controls where Houmao places files, and Kimi Code sees those files when a later Kimi Code launch uses that same home as `KIMI_CODE_HOME`, loads the path through `--skills-dir`, or includes it through `extra_skill_dirs`.

#### Scenario: Help lists Kimi and universal target semantics
- **WHEN** an operator reads `houmao-mgr system-skills install --help`
- **THEN** the help identifies `kimi` as Kimi Code CLI
- **AND THEN** the help warns that `kimi` is not the legacy MoonshotAI `kimi-cli`
- **AND THEN** the help identifies `universal` as the `~/.agents/skills` cross-client Agent Skills target

#### Scenario: Kimi-code selector is rejected
- **WHEN** an operator runs `houmao-mgr system-skills install --tool kimi-code --skill houmao-agent-definition`
- **THEN** the command fails before installing any selected skill
- **AND THEN** the diagnostic tells the operator to use `kimi` for Kimi Code CLI

#### Scenario: Kimi output uses accurate discovery wording
- **WHEN** an operator runs a plain-output Kimi system-skills install, status, or uninstall command
- **THEN** the output reports the resolved Kimi Code home and projected `skills/` path
- **AND THEN** the output does not say that `$KIMI_CODE_HOME/skills` is not automatically discovered by Kimi Code
