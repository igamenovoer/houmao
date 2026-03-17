## MODIFIED Requirements

### Requirement: Launcher config files are schema-validated
The launcher SHALL validate the config file against a schema and fail fast with actionable errors when the config is invalid.

The launcher SHALL reject:
- unknown keys (typo protection),
- invalid enum values (for example proxy policy not in `{clear, inherit}`), and
- structurally invalid values (for example malformed base URLs or non-positive timeouts).

The launcher SHALL accept loopback `base_url` values only when all of the following are true:
- the URL uses the `http` scheme,
- the host is `localhost` or `127.0.0.1`, and
- the URL includes an explicit port.

The launcher SHALL reject non-loopback hosts, missing ports, and malformed CAO base URLs.

The launcher SHALL treat an omitted `home_dir` or a blank-string `home_dir` as "use the launcher-derived system-defined home" rather than rejecting that config.

Repository-owned checked-in configs MAY express that portable default explicitly as `home_dir = ""`.

#### Scenario: Unknown config keys are rejected
- **WHEN** the launcher loads a config file that contains an unknown key
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Invalid enum values are rejected
- **WHEN** the launcher loads a config file whose proxy policy value is not one of `clear` or `inherit`
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Non-default loopback port values are accepted
- **WHEN** the launcher loads a config file whose `base_url` is `http://127.0.0.1:9991`
- **THEN** the launcher accepts that config as a supported loopback CAO target

#### Scenario: Empty home_dir selects the launcher-derived default home
- **WHEN** the launcher loads a config file whose `home_dir` is the empty string
- **THEN** the launcher normalizes that config to the same effective behavior as an omitted `home_dir`
- **AND THEN** it does not fail solely because the checked-in config expressed the default home selection explicitly

#### Scenario: Checked-in local config can express the portable default explicitly
- **WHEN** a repository-owned launcher config uses `home_dir = ""` as its checked-in default
- **THEN** the launcher accepts that config and derives the effective CAO home from `runtime_root/cao_servers/<host>-<port>/home`
- **AND THEN** developers do not need to edit a machine-specific absolute launcher-home path before using that config

#### Scenario: Invalid CLI override values are rejected
- **WHEN** the launcher is invoked with a CLI override whose effective `base_url` uses a non-loopback host or omits an explicit port
- **THEN** the launcher fails with an explicit validation error for that override

#### Scenario: Unsupported base_url values are rejected
- **WHEN** the launcher loads a config file whose `base_url` uses a non-loopback host or omits an explicit port
- **THEN** the launcher fails with an explicit validation error

### Requirement: Launcher home directory anchors CAO state and process HOME
The launcher SHALL treat CAO `HOME` as launcher-owned mutable service state that is distinct from the shared registry root and from agent workdirs.

The launcher SHALL support an optional `home_dir` setting that is applied to the launched `cao-server` process as its `HOME` value.

When launcher config and CLI overrides do not provide an explicit `runtime_root`, and `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the launcher SHALL use that env-var value as the effective runtime root before deriving launcher artifacts or a default `home_dir`.

When launcher config or CLI overrides omit `home_dir`, or provide it as a blank string, the launcher SHALL derive the effective CAO home from the launcher-managed server root for the selected host and port rather than requiring a host-specific absolute path in checked-in config.

#### Scenario: Omitted home_dir derives the launcher-managed default home
- **WHEN** a developer starts launcher-managed CAO with no explicit `home_dir`
- **THEN** the launcher derives the effective CAO home under `runtime_root/cao_servers/<host>-<port>/home`
- **AND THEN** the launched `cao-server` process uses that derived home as its `HOME`

#### Scenario: Blank home_dir derives the same launcher-managed default home
- **WHEN** a developer starts launcher-managed CAO with `home_dir = ""`
- **THEN** the launcher derives the effective CAO home under `runtime_root/cao_servers/<host>-<port>/home`
- **AND THEN** the launched `cao-server` process uses that derived home as its `HOME`
- **AND THEN** the checked-in config remains portable across machines that do not share one writable absolute launcher-home path
