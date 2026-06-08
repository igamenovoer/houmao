# component-agent-construction Specification

## ADDED Requirements

### Requirement: Managed Kimi brain construction exposes projected skills through additive Kimi config

When brain construction or launch preparation builds a managed runtime home for tool `kimi`, the system SHALL continue to project selected private skills and Houmao-owned system skills into the Kimi adapter's configured skill destination under the managed runtime home.

When that managed Kimi projected skill root contains selected skills or Houmao-owned system skills, the system SHALL make that root discoverable to Kimi Code by ensuring the effective managed Kimi `config.toml` includes the absolute projected skill root in `extra_skill_dirs`.

The system SHALL treat this `extra_skill_dirs` update as additive provider configuration. It SHALL preserve unrelated existing Kimi config values, avoid duplicate projected-root entries, and not overwrite an existing `extra_skill_dirs` list except to add the managed projected skill root when missing.

The system SHALL NOT rely on `<KIMI_CODE_HOME>/skills` being auto-discovered by Kimi Code. The system SHALL NOT inject `--skills-dir` into maintained Kimi TUI/local-interactive launches to make managed skills visible.

The maintained Kimi headless backend MAY continue to own headless prompt-mode `--skills-dir` behavior when launching through `kimi_headless`.

#### Scenario: Managed Kimi build writes additive skill directory config

- **WHEN** brain construction builds a managed Kimi runtime home with selected system skills
- **THEN** the selected skills are projected under the Kimi adapter's managed skill destination
- **AND THEN** the effective Kimi `config.toml` includes that absolute projected skill root in `extra_skill_dirs`

#### Scenario: Existing Kimi config is preserved

- **WHEN** a managed Kimi runtime home already has `config.toml` with unrelated settings and existing `extra_skill_dirs`
- **AND WHEN** brain construction or launch preparation adds the managed projected skill root
- **THEN** the unrelated settings remain present
- **AND THEN** the existing extra skill directories remain present
- **AND THEN** the managed projected skill root appears only once

#### Scenario: TUI launch does not use headless-only skill flag

- **WHEN** a managed Kimi agent launches through local interactive TUI posture
- **THEN** the launch command does not receive a Houmao-injected `--skills-dir` argument
- **AND THEN** managed projected skills are made reachable through Kimi `extra_skill_dirs` instead

#### Scenario: Kimi home alone is not treated as skill discovery

- **WHEN** the managed Kimi runtime home is selected with `KIMI_CODE_HOME`
- **THEN** the system does not assume that `<KIMI_CODE_HOME>/skills` is automatically scanned by Kimi Code
- **AND THEN** it configures the managed projected skill root through Kimi-supported additive configuration when managed skills must be visible
