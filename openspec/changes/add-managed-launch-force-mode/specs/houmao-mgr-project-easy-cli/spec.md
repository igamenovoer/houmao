## ADDED Requirements

### Requirement: `project easy instance launch` supports launch-owned managed force takeover

`houmao-mgr project easy instance launch` SHALL accept optional `--force` for delegated managed takeover on the current easy-launch invocation.

`--force` MAY be supplied bare or with an explicit mode value.

Bare `--force` SHALL default to mode `keep-stale`.

The only supported explicit force mode values SHALL be `keep-stale` and `clean`.

The selected force mode SHALL be forwarded to the delegated native managed launch for the current invocation only and SHALL NOT be persisted into the stored specialist or easy profile.

When no force mode is supplied and the delegated native launch resolves a fresh existing owner for the target managed identity, easy instance launch SHALL fail rather than replacing it.

When `--force` is supplied, easy instance launch SHALL request the corresponding managed runtime takeover for the resolved managed identity whether that identity comes from direct `--name` or from an easy-profile default.

#### Scenario: Bare `--force` defaults to `keep-stale` for specialist-backed launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --force`
- **AND WHEN** a fresh live session already owns managed identity `repo-research-1`
- **THEN** the delegated launch requests managed takeover in mode `keep-stale`
- **AND THEN** the stored specialist remains unchanged

#### Scenario: Easy-profile-backed launch can request explicit `clean` without rewriting the profile
- **WHEN** easy profile `alice` stores default managed-agent name `alice`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --force clean`
- **AND WHEN** a fresh live session already owns managed identity `alice`
- **THEN** the delegated launch requests managed takeover in mode `clean`
- **AND THEN** stored easy profile `alice` remains unchanged and does not gain a persisted force mode

#### Scenario: Missing `--force` preserves the existing ownership conflict failure
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** a fresh live session already owns managed identity `repo-research-1`
- **THEN** the command fails rather than replacing that existing live owner
