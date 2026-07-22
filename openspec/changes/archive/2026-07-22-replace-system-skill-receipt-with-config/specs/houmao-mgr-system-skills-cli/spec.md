## ADDED Requirements

### Requirement: System-skills CLI reports skill configuration terminology
Structured install, upgrade, and uninstall results SHALL expose `config_path`. Structured status and doctor results SHALL expose config evidence under `config`. Current structured output SHALL NOT expose `receipt`, `receipt_path`, or receipt-specific status fields.

Plain install, status, doctor, and upgrade output SHALL label the file `Skill config:` and SHALL NOT label current state as a receipt.

#### Scenario: Install reports config path
- **WHEN** an operator installs a pack with structured output
- **THEN** the result contains `config_path` ending in `houmao-skill-config.json`
- **AND THEN** the result contains no `receipt_path`

#### Scenario: Status uses config evidence
- **WHEN** an operator inspects a config-managed home
- **THEN** structured status reports the config state, path, Houmao version, and derived selected packs under `config`
- **AND THEN** plain status labels the same path `Skill config:`
- **AND THEN** neither output uses receipt terminology

### Requirement: Doctor remains independent of skill config ownership
`houmao-mgr system-skills doctor` SHALL inspect expected installed roots and their top-level `houmao_version` values directly. Missing `houmao-skill-config.json` SHALL NOT by itself make a complete and release-matching copy-paste or Skills CLI installation unhealthy.

Doctor SHALL report config evidence separately when present and SHALL use config terminology in both plain and structured output.

#### Scenario: Configless static pack is healthy
- **WHEN** doctor inspects a complete static pack whose roots and frontmatter match the running release but no skill config exists
- **THEN** doctor reports all expected members healthy
- **AND THEN** it reports config state as absent

#### Scenario: Config release is diagnostic evidence
- **WHEN** doctor inspects a config-managed pack
- **THEN** it reports the config's `houmao_version` separately from each installed root's observed frontmatter version
- **AND THEN** the config value does not replace direct installed-root evidence
