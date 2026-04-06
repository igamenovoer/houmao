## ADDED Requirements

### Requirement: `houmao-mgr agents join` exposes an explicit opt-out for default Houmao-owned system-skill installation
`houmao-mgr agents join` SHALL expose `--no-install-houmao-skills` as the explicit operator opt-out for default Houmao-owned system-skill installation during session adoption.

When that flag is omitted, a successful join SHALL attempt the catalog-driven managed-join Houmao-owned current-skill installation before publishing the joined session.

When that flag is present, the join workflow SHALL continue without mutating the adopted tool home through the default Houmao-owned system-skill installer.

#### Scenario: Join help shows the explicit opt-out flag
- **WHEN** an operator runs `houmao-mgr agents join --help`
- **THEN** the help output lists `--no-install-houmao-skills`
- **AND THEN** the flag is described as the explicit opt-out for default Houmao-owned skill installation during adoption

#### Scenario: Join without the opt-out attempts managed-join set installation before publish
- **WHEN** an operator runs `houmao-mgr agents join --agent-name worker`
- **AND WHEN** default Houmao-owned skill installation is enabled for that adoption
- **THEN** the join workflow attempts the current Houmao-owned skill installation resolved from the catalog’s managed-join set list before publishing the joined session
- **AND THEN** later managed-session metadata reflects a join that completed with the default Houmao-owned installation path enabled

#### Scenario: Join opt-out skips default Houmao-owned tool-home mutation
- **WHEN** an operator runs `houmao-mgr agents join --agent-name worker --no-install-houmao-skills`
- **THEN** the join workflow may continue without performing the default Houmao-owned system-skill installation
- **AND THEN** the command does not mutate the adopted tool home through that default installer path
