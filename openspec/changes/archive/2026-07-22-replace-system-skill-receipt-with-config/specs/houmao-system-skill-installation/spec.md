## ADDED Requirements

### Requirement: Houmao stores minimal system-skill ownership configuration
The system SHALL store manager-owned system-skill lifecycle state at `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json` using schema `houmao-skill-config.v1`.

The top-level payload SHALL contain exactly `schema_version`, `houmao_version`, `projection_mode`, and `skills`. Each installed-skill record SHALL contain exactly `name`, `relative_path`, `content_digest`, and `owning_pack_ids`. The configuration SHALL NOT duplicate its tool, home path, manifest schema, selected pack set, timestamps, operation history, skill role, activation posture, per-skill projection mode, per-skill release version, or source path.

The selected installed pack set SHALL be derived from the manifest-ordered union of per-skill `owning_pack_ids`. The parser SHALL reject malformed, unknown, duplicate, unsafe, empty, or internally inconsistent state.

#### Scenario: Fresh admin symlink installation writes minimal config
- **WHEN** Houmao installs the static admin pack into a clean Kimi home in symlink mode
- **THEN** it writes `houmao-skill-config.json` below the Kimi tool-scoped Houmao state directory
- **AND THEN** the config records the installing Houmao release and `symlink` collection mode
- **AND THEN** its skill records identify the five installed roots, their relative paths, content digests, and admin ownership
- **AND THEN** it contains no field outside the strict minimal schema

#### Scenario: Combined installation derives both packs
- **WHEN** a valid config contains the six unique roots belonging to the installed admin and agent packs
- **THEN** the lifecycle derives `admin` and `agent` from the member owner sets
- **AND THEN** the three shared roots record both owners without a serialized selected-pack field

### Requirement: Skill config is the sole source of manager ownership
Install, sync, status, upgrade, and uninstall SHALL treat only a valid `houmao-skill-config.json` as persisted manager ownership evidence. A same-name destination without that config ownership SHALL remain an unowned collision and SHALL NOT be overwritten or deleted implicitly.

Lifecycle mutations SHALL commit and validate affected projections before atomically writing the config. Rollback SHALL restore the preceding new-format config and affected projection state. Partial uninstall SHALL subtract the requested pack owner and retain roots that have another owner; final uninstall SHALL remove the config rather than persist an empty skill list.

#### Scenario: Partial uninstall retains shared roots
- **WHEN** admin and agent ownership are installed and the operator uninstalls agent
- **THEN** the agent entrypoint is removed if unchanged
- **AND THEN** shared routines and both loop roots remain owned by admin
- **AND THEN** the rewritten config derives only the admin pack

#### Scenario: Final uninstall removes config
- **WHEN** the last installed pack is uninstalled from an unchanged managed collection
- **THEN** its final-owner projections are removed
- **AND THEN** `houmao-skill-config.json` is removed
- **AND THEN** no empty config is written

### Requirement: Receipt persistence is unsupported
The system SHALL NOT probe, read, parse, migrate, delete, or report any `receipt.json` as current system-skill lifecycle state. Receipt schema identifiers and receipt-specific inspection states SHALL NOT be part of the current lifecycle model.

Users with a receipt-based installation MUST remove or uninstall that installation and perform a clean reinstall before the new lifecycle can manage it.

#### Scenario: Old receipt and projected roots remain unowned
- **WHEN** a tool home contains `receipt.json` and old projected Houmao skill roots but no `houmao-skill-config.json`
- **THEN** the current lifecycle ignores `receipt.json`
- **AND THEN** it treats the projected roots as unowned collisions
- **AND THEN** installation fails without overwriting or deleting them

#### Scenario: Old receipt alone is ignored
- **WHEN** a tool home contains `receipt.json` but no projected Houmao skill roots and no new config
- **THEN** status reports no current config ownership
- **AND THEN** the lifecycle does not remove or rewrite the old file
