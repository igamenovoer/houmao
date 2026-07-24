## Purpose
Define the operator-facing `houmao-mgr system-skills` CLI for listing, installing, and inspecting Houmao-owned system skills.
## Requirements
### Requirement: System-skills doctor diagnoses an expected static pack
`houmao-mgr system-skills doctor` SHALL perform a read-only diagnostic of repeatable `--pack admin|agent` selections. Omitted pack selection SHALL default to `agent`.

Doctor SHALL check every expected standalone root for destination shape, complete owned content, valid matching name frontmatter, and exact `houmao_version` equality with the running Houmao package. It SHALL check the shared root for the exact sixteen parent-scoped child entrypoints.

#### Scenario: Healthy managed agent pack
- **WHEN** doctor examines a complete current agent pack
- **THEN** it reports the agent entrypoint, shared routines, pro loop, and lite loop as healthy
- **AND THEN** it reports every observed `houmao_version` as equal to the running package version

#### Scenario: Expected root is absent
- **WHEN** doctor examines an agent pack without `houmao-shared-routines`
- **THEN** it reports that expected root as absent
- **AND THEN** the aggregate diagnostic is unhealthy

### Requirement: Doctor supports explicit home and managed-agent targets
Doctor SHALL support an explicit tool-home mode using `--tool` and the existing optional `--home` resolution. It SHALL also support managed-agent mode using exactly one of `--agent-id` or `--agent-name`.

Managed-agent mode SHALL resolve one known local managed-agent record, its session manifest, its brain manifest, its tool, and its persistent home. It SHALL reject ambiguous names, external agents, missing authority files, and combinations of managed-agent selectors with `--tool` or `--home`.

#### Scenario: Operator diagnoses by agent id
- **WHEN** an operator runs doctor with one authoritative managed-agent id
- **THEN** doctor resolves that agent's tool and persistent home without requiring a live session
- **AND THEN** it checks the expected agent pack in that home

#### Scenario: Friendly name is ambiguous
- **WHEN** `--agent-name` resolves to more than one known managed agent
- **THEN** doctor fails target resolution before inspecting any home
- **AND THEN** it asks for an authoritative agent id

#### Scenario: Operator provides incompatible target modes
- **WHEN** a doctor request combines `--agent-id` with `--tool` or `--home`
- **THEN** the command rejects the request as invalid usage
- **AND THEN** it does not inspect or mutate either target

### Requirement: Doctor separates installation integrity from version status
Structured doctor output SHALL include the resolved target, expected running Houmao version, selected packs, config posture, aggregate health, and one record per expected standalone skill.

Each member record SHALL include its name, role, destination, integrity status, observed version when available, version status, and issue details. Version status SHALL distinguish `match`, `mismatch`, `missing`, `invalid`, and `unavailable`.

#### Scenario: Version matches but content was edited
- **WHEN** an installed root retains the current `houmao_version` but its owned content differs from the packaged source
- **THEN** doctor reports version status `match` and integrity status `drifted`
- **AND THEN** the aggregate diagnostic is unhealthy

#### Scenario: Old release is structurally complete
- **WHEN** every expected root is complete but declares an older valid `houmao_version`
- **THEN** doctor reports each differing value as `mismatch`
- **AND THEN** it reports the running package version as the expected value

#### Scenario: Running version is unavailable
- **WHEN** the running package reports `0+unknown`
- **THEN** doctor reports version comparison as `unavailable`
- **AND THEN** it does not claim a version match

### Requirement: Doctor handles configless and config-managed homes
Doctor SHALL read installed frontmatter as the version authority. A current skill config MAY add ownership and projection evidence, but its `houmao_version` SHALL NOT substitute for installed skill metadata.

Config absence alone SHALL NOT make an otherwise complete externally installed pack unhealthy. Corrupt, unsupported, or inconsistent config evidence SHALL be reported separately and SHALL NOT prevent direct read-only frontmatter inspection.

#### Scenario: Config release differs from installed metadata
- **WHEN** a config records one Houmao release and an installed root declares another
- **THEN** doctor reports the installed frontmatter value as the observed skill version
- **AND THEN** it reports config evidence separately

#### Scenario: Complete configless copy matches
- **WHEN** a copy-paste installation contains every expected current root and no skill config
- **THEN** doctor reports config posture `absent`
- **AND THEN** it can still report the selected pack as healthy

### Requirement: Doctor uses diagnostic exit semantics without enforcement
Doctor SHALL exit with code 0 only when every expected root is complete and version-matched. It SHALL exit with code 1 for detected missing, malformed, incomplete, drifted, conflicting, mismatched, or unavailable health evidence. Click usage and target-resolution errors SHALL retain code 2.

Doctor SHALL NOT mutate files, install or remove skills, write a config, launch an agent, or change any lifecycle state.

#### Scenario: Automation checks an outdated home
- **WHEN** doctor detects one version mismatch
- **THEN** it emits the complete diagnostic and exits with code 1
- **AND THEN** the installed home remains byte-for-byte unchanged

#### Scenario: Automation checks a healthy home
- **WHEN** all expected members are complete and version-matched
- **THEN** doctor exits with code 0
- **AND THEN** it performs no lifecycle mutation

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

### Requirement: System-skills CLI exposes pack lifecycle commands
`houmao-mgr system-skills` SHALL expose `list`, `install`, `status`, `doctor`, `upgrade`, and `uninstall` for Houmao system-skill packs.

The command group SHALL manage standalone pack projections and the tool-scoped skill config. It SHALL NOT expose parent-scoped shared children or managed auto skills as independent install units.

#### Scenario: Operator opens system-skills help
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** help lists all six lifecycle and diagnostic commands
- **AND THEN** it describes shared children as parent-scoped routes rather than install selectors

### Requirement: System-skills CLI retains supported target and output behavior
Pack lifecycle commands SHALL retain effective-home resolution, explicit tool-home overrides, plain output, and root `--print-json` structured output for Claude, Codex, Copilot, Kimi, and universal targets.

The CLI SHALL NOT claim Gemini system-skill support. Path output SHALL report standalone projection paths and the tool-scoped config path; parent-scoped child paths MAY appear only as inspection detail.

#### Scenario: Structured Codex install output is requested
- **WHEN** an operator runs root `--print-json` with a Codex admin-pack install
- **THEN** output reports the resolved home, `admin` pack, five standalone paths, config path, and projection mode
- **AND THEN** it does not report each shared child as a top-level installed skill

### Requirement: System-skills list reports the static collection and pack membership
`houmao-mgr system-skills list` SHALL report the six standalone skill names, the sixteen shared child logical ids, admin and agent pack member lists, default lanes, and activation posture.

Plain and structured output SHALL distinguish standalone install units from parent-scoped routines. It SHALL NOT describe shared routines as a protected mount or either loop as a shared child.

#### Scenario: Operator lists current system skills
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output reports six standalone skills
- **AND THEN** it reports five admin members and four agent members
- **AND THEN** it identifies the three overlapping members and sixteen shared children

### Requirement: System-skills install manages complete static packs
`houmao-mgr system-skills install` SHALL accept repeatable `--pack admin|agent` selection plus supported tool, home, and copy or symlink options. Omitted external selection SHALL resolve admin.

The result SHALL report selected packs, deduplicated standalone members, top-level destination paths, projection mode, and `config_path`. It SHALL NOT report a composed mount path or materialization root.

#### Scenario: Operator installs both packs
- **WHEN** an operator selects both admin and agent
- **THEN** the command installs six unique top-level roots transactionally
- **AND THEN** output reports shared ownership for shared routines, pro loop, and lite loop

### Requirement: System-skills status reports static integrity and owner sets
`houmao-mgr system-skills status` SHALL classify each installed pack and each config-owned standalone member as absent, complete, incomplete, drifted, or conflicting. It SHALL report config posture, owner pack ids, content digest posture, projection mode, and legacy flat-path evidence.

Status SHALL validate shared child completeness inside `houmao-shared-routines` without treating child paths as independent projections.

#### Scenario: Shared routines is missing from an agent installation
- **WHEN** the config owns agent but the shared-routines path is absent
- **THEN** status reports the agent pack as incomplete
- **AND THEN** it identifies the missing shared dependency

### Requirement: System-skills upgrade refreshes config-owned static packs
`houmao-mgr system-skills upgrade` SHALL refresh a current config-owned static collection or install into a clean target through staged validation and transactional commit.

Upgrade SHALL NOT read or migrate an old `receipt.json`. Same-name roots without current config ownership SHALL remain unowned collisions. Independently recognized legacy flat paths MAY be removed only with package-link or known-digest evidence.

#### Scenario: Operator upgrades a current admin pack
- **WHEN** an operator upgrades a healthy config-owned admin installation
- **THEN** the command refreshes all five static admin members
- **AND THEN** it writes the skill config only after successful validation

#### Scenario: Operator points upgrade at an old receipt-era installation
- **WHEN** old projected roots exist without `houmao-skill-config.json`
- **THEN** upgrade reports an unowned collision
- **AND THEN** it preserves the old roots for explicit clean reinstall

### Requirement: System-skills uninstall honors overlapping ownership
`houmao-mgr system-skills uninstall` SHALL remove selected pack ownership transactionally and SHALL remove a standalone projection only after its last owner is removed.

Plain and structured output SHALL distinguish removed exclusive members, retained shared members, absent members, and preserved conflicts.

#### Scenario: Operator uninstalls agent while admin remains
- **WHEN** both packs are installed and the operator uninstalls agent
- **THEN** the command removes only the agent entrypoint
- **AND THEN** it retains shared routines and both loop skills for admin

### Requirement: System-skills CLI rejects dynamic-composition terminology and selectors
Current help and diagnostics SHALL describe static standalone members and shared parent-scoped routines. Protected mount ids, protected logical install selectors, materialized composition paths, and old set selectors SHALL NOT appear as supported current inputs.

#### Scenario: Operator requests a protected mount id
- **WHEN** an operator attempts to install `houmao-shared-routines` as a protected mount selector
- **THEN** the command rejects that obsolete selector form
- **AND THEN** it explains that shared routines is a standalone member installed through an actor pack
