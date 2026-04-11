## ADDED Requirements

### Requirement: `houmao-mgr` exposes `internals` as a top-level utility command family
`houmao-mgr` SHALL expose `internals` as a top-level native command family.

The `internals` command family SHALL contain Houmao-owned internal utility surfaces that support agent and maintainer workflows without becoming user-facing managed-agent lifecycle commands.

At minimum, `internals` SHALL include a nested `graph` command family for NetworkX-backed graph tooling.

The root help surface SHALL list `internals` alongside the other top-level command families.

The `internals` command family SHALL respect the root print-style flags by using the shared `houmao-mgr` output engine for structured command results.

#### Scenario: Root help shows internals
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `internals` among the supported top-level command families
- **AND THEN** the help output does not present `internals` as a replacement for `agents`, `server`, `project`, or `system-skills`

#### Scenario: Internals help shows graph tooling
- **WHEN** an operator runs `houmao-mgr internals --help`
- **THEN** the help output includes the `graph` command family
- **AND THEN** the command is described as an internal utility surface

#### Scenario: Graph command output honors print-json
- **WHEN** an operator runs an `internals graph` command with the root `--print-json` flag
- **THEN** the command emits machine-readable JSON through the shared output engine
- **AND THEN** it does not bypass the configured print style with ad hoc printing for structured payloads
