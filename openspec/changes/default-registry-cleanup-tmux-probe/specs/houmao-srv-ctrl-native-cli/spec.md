## MODIFIED Requirements

### Requirement: `houmao-mgr admin cleanup` exposes grouped local cleanup commands
`houmao-mgr` SHALL expose a native `admin cleanup` command group for local cleanup operations.

At minimum, the documented grouped cleanup tree SHALL include:

- `registry`
- `runtime sessions`
- `runtime builds`
- `runtime logs`
- `runtime mailbox-credentials`

This grouped cleanup tree SHALL be documented as local maintenance over local Houmao-owned state rather than as a pair-managed server API surface.

Within that grouped tree, `houmao-mgr admin cleanup registry` SHALL perform local tmux liveness probing by default for tmux-backed records and SHALL expose `--no-tmux-check` as the explicit opt-out flag for lease-only behavior.

The compatibility alias `houmao-mgr admin cleanup-registry` SHALL preserve the same registry-cleanup behavior and flag contract.

#### Scenario: Native help surface shows grouped cleanup commands
- **WHEN** an operator runs `houmao-mgr admin cleanup --help`
- **THEN** the help output lists `registry` and the `runtime` cleanup family
- **AND THEN** the grouped cleanup surface is presented as local maintenance rather than a server-backed admin API

#### Scenario: Registry cleanup help shows the opt-out tmux flag
- **WHEN** an operator runs `houmao-mgr admin cleanup registry --help`
- **THEN** the help output includes `--no-tmux-check`
- **AND THEN** the help output does not require `--probe-local-tmux` to enable default tmux probing

#### Scenario: Registry cleanup defaults to tmux probing
- **WHEN** an operator runs `houmao-mgr admin cleanup registry`
- **AND WHEN** a lease-fresh tmux-backed registry record points at a tmux session that is absent on the local host
- **THEN** `houmao-mgr` classifies that record as stale by default
- **AND THEN** the operator does not need an extra flag to perform local tmux-aware cleanup
