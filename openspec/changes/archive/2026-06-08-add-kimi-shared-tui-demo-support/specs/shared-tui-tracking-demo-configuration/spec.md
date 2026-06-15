## ADDED Requirements

### Requirement: Demo config SHALL define Kimi tool defaults
The restored shared TUI tracking demo pack's checked-in `demo-config.toml` SHALL define a `tools.kimi` section.

The Kimi tool config SHALL provide the default Kimi interactive-watch recipe path and MAY define Kimi-specific launch overrides or operator prompt mode defaults using the same merge and validation rules as other supported tools.

The demo config parser and packaged JSON Schema SHALL include Kimi in the supported tool section for full config documents, profile overrides, scenario overrides, and CLI-derived overrides.

#### Scenario: Maintainer inspects Kimi config defaults
- **WHEN** a maintainer opens `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml`
- **THEN** it contains a `tools.kimi` section
- **AND THEN** that section points to the demo-local Kimi interactive-watch recipe

#### Scenario: Kimi config validates through the packaged schema
- **WHEN** a maintainer validates the checked-in demo config through the demo config boundary models
- **THEN** the Kimi tool section is accepted as part of the supported config contract
- **AND THEN** the packaged JSON Schema describes Kimi tool config fields

### Requirement: Demo config SHALL allow Kimi scenario and profile overrides
The restored demo config resolution workflow SHALL allow Kimi-specific config overrides through the same profile, scenario, and CLI override mechanisms used for other supported tools.

A Kimi scenario override SHALL be able to adjust Kimi recipe path, launch overrides, evidence cadence, ready timeout, semantic settle time, and presentation settings without changing the checked-in default Kimi config.

#### Scenario: Kimi scenario override changes launch recipe
- **WHEN** a Kimi recorded-capture scenario has a matching scenario override in the selected demo config
- **THEN** config resolution applies that override before CLI overrides
- **AND THEN** the Kimi workflow uses the resolved recipe path from the merged config

#### Scenario: Kimi CLI recipe override wins last
- **WHEN** a maintainer starts a Kimi demo command with `--recipe`
- **THEN** the CLI recipe override wins over the checked-in Kimi default and any profile or scenario override
- **AND THEN** the resolved config persisted with the run records the effective Kimi recipe path
