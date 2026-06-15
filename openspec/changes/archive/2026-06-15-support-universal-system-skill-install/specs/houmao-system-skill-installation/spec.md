## ADDED Requirements

### Requirement: Shared installer supports the universal Agent Skills projection target
The shared system-skill installer SHALL support `universal` as an explicit installation target for Houmao-owned system skills.

For the `universal` target, the visible projected paths SHALL use the cross-client Agent Skills root:

- Universal: `skills/<houmao-skill>/` under the resolved universal home root, which defaults to `~/.agents` for the operator CLI.

The shared installer SHALL apply the same current-skill selection, retired-skill cleanup, status discovery, uninstall, copied projection, and symlink projection behavior to the `universal` target that it applies to existing `skills/`-root targets.

The `universal` target SHALL NOT imply a runtime tool adapter, credential home, launch backend, or managed-agent provider.

Houmao-managed launch and managed join flows SHALL continue installing managed system skills into the selected runtime tool home and SHALL NOT silently duplicate those skills into the `universal` target.

#### Scenario: Explicit universal copy installation projects selected skills under skills root
- **WHEN** Houmao installs selected current system skills for target `universal` into resolved home `/home/alice/.agents` without symlink projection
- **THEN** each selected skill is copied under `/home/alice/.agents/skills/<houmao-skill>/`
- **AND THEN** the result reports projected relative directories under `skills/`

#### Scenario: Explicit universal symlink installation uses existing projection mode
- **WHEN** Houmao installs one selected current system skill for target `universal` with symlink projection
- **THEN** the projected path is `skills/<houmao-skill>/`
- **AND THEN** that path is a directory symlink to the packaged skill asset root

#### Scenario: Universal uninstall removes only universal projections
- **WHEN** Houmao uninstalls system skills for target `universal` with resolved home `/home/alice/.agents`
- **THEN** it removes current and retired Houmao-owned projections under `/home/alice/.agents/skills/`
- **AND THEN** it does not remove projections from `.codex/skills/`, `.kimi-code/skills/`, `.gemini/skills/`, `.github/skills/`, or `.claude/skills/`

#### Scenario: Managed runtime install does not write universal target
- **WHEN** Houmao builds or joins a managed runtime home for one concrete agent tool
- **THEN** managed system skills are installed into that runtime tool home's native projection root
- **AND THEN** Houmao does not also install those skills into `~/.agents/skills`

### Requirement: Kimi system-skill projection targets Kimi Code CLI homes
The shared system-skill target `kimi` SHALL refer to Kimi Code CLI.

For the `kimi` target, the visible projected paths SHALL use `skills/<houmao-skill>/` under the resolved Kimi Code home, including `$KIMI_CODE_HOME/skills/<houmao-skill>/` when Kimi Code is launched with that home and the project default `.kimi-code/skills/<houmao-skill>/` when Houmao resolves a project-scoped Kimi Code home.

The `kimi` target SHALL NOT represent the legacy MoonshotAI `kimi-cli` project as a separate installation profile.

#### Scenario: Kimi projection uses the resolved Kimi Code home skills root
- **WHEN** Houmao installs selected current system skills for target `kimi` into resolved Kimi Code home `/tmp/kimi-home`
- **THEN** each selected skill is projected under `/tmp/kimi-home/skills/<houmao-skill>/`
- **AND THEN** the projected relative directory is `skills/<houmao-skill>`

#### Scenario: Kimi and universal targets remain separate
- **WHEN** Houmao installs selected current system skills for target `kimi`
- **THEN** it does not install those skills into `~/.agents/skills`
- **AND WHEN** Houmao installs selected current system skills for target `universal`
- **THEN** it does not install those skills into the resolved Kimi Code home
