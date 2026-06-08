# houmao-mgr-system-skills-cli Specification

## ADDED Requirements

### Requirement: `houmao-mgr system-skills` supports Kimi projection without overstating discovery

`houmao-mgr system-skills install`, `status`, and `uninstall` SHALL accept `kimi` as a supported `--tool` value.

For Kimi, omitted-home resolution SHALL use this precedence:

1. explicit `--home`
2. `KIMI_CODE_HOME`
3. `<cwd>/.kimi-code`

For Kimi, Houmao-owned skills SHALL project under `<effective-home>/skills/`.

Plain install, status, and uninstall output for Kimi SHALL distinguish the effective home from the projected skill paths. The output and documentation SHALL NOT claim that arbitrary `<KIMI_CODE_HOME>/skills` paths are automatically discovered by Kimi Code.

When omitted-home Kimi resolution chooses `<cwd>/.kimi-code`, the command MAY describe the projection as project-local Kimi skill material for Kimi runs whose project discovery includes that `.kimi-code/skills` root.

Manual `system-skills install --tool kimi` SHALL remain a projection command and SHALL NOT rewrite Kimi `config.toml` for arbitrary external homes. Managed Kimi runtime homes SHALL rely on brain construction or launch preparation to add managed projected skill roots through Kimi `extra_skill_dirs`.

#### Scenario: Omitted-home Kimi install uses the project `.kimi-code` home

- **WHEN** an operator runs `houmao-mgr system-skills install --tool kimi --skill houmao-agent-definition` from `/workspace/repo`
- **AND WHEN** no `KIMI_CODE_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command uses `/workspace/repo/.kimi-code` as the effective Kimi home
- **AND THEN** the selected skill is projected under `/workspace/repo/.kimi-code/skills/houmao-agent-definition/`

#### Scenario: Kimi status honors `KIMI_CODE_HOME`

- **WHEN** `KIMI_CODE_HOME=/tmp/kimi-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills status --tool kimi`
- **THEN** the command inspects `/tmp/kimi-home` as the effective Kimi home
- **AND THEN** it reports discovered Houmao-owned skill projections under `/tmp/kimi-home/skills/`
- **AND THEN** it does not report that Kimi Code necessarily auto-discovers that path

#### Scenario: Explicit Kimi home remains a projection target

- **WHEN** an operator runs `houmao-mgr system-skills install --tool kimi --home /tmp/external-kimi-home --skill houmao-credential-mgr`
- **THEN** the command projects the selected skill under `/tmp/external-kimi-home/skills/houmao-credential-mgr/`
- **AND THEN** the command does not mutate `/tmp/external-kimi-home/config.toml`
- **AND THEN** the output does not imply that this explicit home is automatically part of Kimi Code's native skill discovery

#### Scenario: Multi-tool install accepts Kimi

- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex,kimi --skill houmao-agent-messaging` from `/workspace/repo`
- **AND WHEN** no relevant tool-home env vars are set
- **THEN** the command installs Codex skill material under `/workspace/repo/.codex/skills/`
- **AND THEN** it installs Kimi skill material under `/workspace/repo/.kimi-code/skills/`
- **AND THEN** the structured result contains one installation entry for each selected tool

#### Scenario: Kimi uninstall removes only projected Houmao-owned skills

- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool kimi --home /tmp/kimi-home`
- **AND WHEN** `/tmp/kimi-home/skills/houmao-agent-definition/` exists
- **THEN** the command removes the current catalog-known Houmao-owned Kimi skill projection paths under `/tmp/kimi-home/skills/`
- **AND THEN** it leaves unrelated user skills, parent skill roots, and Kimi config files in place
