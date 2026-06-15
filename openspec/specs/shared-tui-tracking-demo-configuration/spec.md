# shared-tui-tracking-demo-configuration Specification

## Purpose
Define the restored shared TUI tracking demo pack's checked-in configuration contract, deterministic resolution behavior, and packaged schema.
## Requirements
### Requirement: The restored demo pack SHALL expose a checked-in demo-owned configuration file

The restored shared TUI tracking demo pack SHALL expose a checked-in configuration file at `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` that defines the demo’s supported defaults and named profiles.

The restored demo pack SHALL also expose a dedicated developer-facing configuration reference document under the same demo directory that explains the supported config sections, merge behavior, profile behavior, sweep behavior, and config selection workflow.

#### Scenario: Maintainer inspects the demo’s supported defaults
- **WHEN** a maintainer opens the restored shared TUI tracking demo pack
- **THEN** a checked-in `demo-config.toml` exists under `scripts/demo/shared-tui-tracking-demo-pack/`
- **AND THEN** a dedicated config reference document exists under the same demo directory

### Requirement: Demo config resolution SHALL be deterministic and persisted with run artifacts

The restored shared TUI tracking demo workflow SHALL resolve effective configuration values in a deterministic order that includes the selected demo-config file, any selected profile overrides, any selected scenario overrides, and any CLI overrides.

The workflow SHALL support the checked-in `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` as the default config source and SHALL also support an alternate config path selected through operator-facing demo commands.

Before a config influences launch, capture, validation, or sweep behavior, the workflow SHALL reject malformed or unsupported config payloads with an error that identifies the selected config file.

Each run SHALL persist the resolved configuration inside the run output so later comparison, reporting, and debugging can identify which launch, evidence, semantic, and presentation settings governed that run.

#### Scenario: Run artifacts explain which settings governed one run
- **WHEN** a maintainer completes a restored live-watch or recorded-validation run
- **THEN** the run output includes the resolved demo configuration that governed that run
- **AND THEN** the persisted config identifies the source config path that governed the run

#### Scenario: Alternate config selection changes the resolved roots and defaults
- **WHEN** a maintainer launches a restored demo command with an alternate demo-config path
- **THEN** the workflow resolves settings from that selected config file instead of the companion default config
- **AND THEN** any config-derived path roots and defaults follow the selected config

#### Scenario: Invalid demo config is rejected before workflow behavior begins
- **WHEN** a maintainer selects a malformed or unsupported demo-config file
- **THEN** the command fails before starting or replaying the demo workflow
- **AND THEN** the error identifies the selected config file and the invalid field or section

### Requirement: Demo config SHALL publish a machine-readable schema

The restored shared TUI tracking demo pack SHALL publish a machine-readable JSON Schema under the demo source package that describes the supported demo-config structure, including top-level config sections and the nested structures used by profiles, scenario overrides, and sweeps.

#### Scenario: Maintainer inspects the source package for the config contract
- **WHEN** a maintainer looks in the restored demo source package for the demo-config contract
- **THEN** a packaged JSON Schema for the demo config is present
- **AND THEN** the schema describes the supported config structure and value shapes for the restored demo workflow

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

