## MODIFIED Requirements

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different responsibilities while making the active project overlay the default local root for non-registry state.

The default per-user shared Houmao root that remains global SHALL be the platformdirs user config path for app name `houmao` and no app author. On Linux this is expected to be `~/.config/houmao`.

The default per-user shared registry root SHALL be:

- registry root: `<platformdirs-user-config>/registry`

For maintained local project-aware command flows, the default overlay-owned roots SHALL be:

- runtime root: `<active-overlay>/runtime`
- mailbox root: `<active-overlay>/mailbox`
- jobs root: `<active-overlay>/jobs`
- agent memory root family: `<active-overlay>/memory/agents/<agent-id>/`
- project catalog/content roots under `<active-overlay>/`
- native-agent compatibility projection root: `<active-overlay>/agents` unless project config selects a different projection path

For each tmux-backed managed agent, the default managed memory paths SHALL be derived as:

- memo file: `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- pages directory: `<active-overlay>/memory/agents/<agent-id>/pages/`

The system SHALL NOT derive current managed-agent memory paths from `<active-overlay>/jobs/<session-id>/`.

The system SHALL continue to support stronger override surfaces for global registry, runtime, and mailbox locations where supported.

When both an explicit CLI/config override and an env-var override exist for the same effective location, the explicit override SHALL win.
When no explicit override exists but a supported env-var override is set, the env-var override SHALL win.
When neither explicit override nor env-var override is supplied for a maintained local project-aware flow, the system SHALL use the overlay-derived defaults above.

#### Scenario: Project-aware local roots resolve managed memory under the active overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root is `/repo/.houmao/mailbox`
- **AND THEN** the effective memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the effective pages directory is `/repo/.houmao/memory/agents/researcher-id/pages`

#### Scenario: Shared registry uses the platformdirs config root by default
- **WHEN** an operator runs maintained local Houmao commands in project context without a registry override
- **THEN** the effective shared registry root is the `registry` child of the platformdirs user config path for `houmao`
- **AND THEN** on ordinary Linux systems that path is `~/.config/houmao/registry`
- **AND THEN** the command does not use `~/.houmao/registry` as the default shared registry

#### Scenario: Home `.houmao` is not an ambient project candidate for nested repositories
- **WHEN** the operator's home directory contains legacy `~/.houmao`
- **AND WHEN** the operator runs a project-aware command from `~/work/repo`
- **THEN** the legacy home-level `.houmao` directory is not treated as the shared registry root
- **AND THEN** it is not selected as a project overlay unless it contains an explicitly selected project config through supported project overlay selection

#### Scenario: Custom project native projection path does not change fixed overlay-owned runtime family
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` selects native projection path `custom-agents`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root remains `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root and memory root family remain `/repo/.houmao/mailbox` and `/repo/.houmao/memory/agents/researcher-id`

## ADDED Requirements

### Requirement: Legacy shared-home paths are not silently migrated by default
The system SHALL NOT silently move, delete, or mutate legacy `~/.houmao` shared-registry data when adopting the platformdirs user config default.

If migration tooling is provided, it SHALL be explicit and SHALL report source and destination paths before mutating either tree.

#### Scenario: Default root change does not mutate legacy home data
- **WHEN** legacy shared registry data exists under `~/.houmao/registry`
- **AND WHEN** the operator runs a Houmao command without a registry override
- **THEN** the command uses the platformdirs config registry root
- **AND THEN** it does not move or delete the legacy `~/.houmao/registry` tree as a side effect
