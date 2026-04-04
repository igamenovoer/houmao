## MODIFIED Requirements

### Requirement: `houmao-mgr admin cleanup runtime` exposes host-scoped runtime janitors
`houmao-mgr` SHALL expose a local `admin cleanup runtime` command family for cleanup work rooted under the effective runtime root.

At minimum, that family SHALL include:

- `sessions`
- `builds`
- `logs`
- `mailbox-credentials`

These commands SHALL operate on local Houmao-owned runtime state and SHALL NOT require a running pair authority.

When no stronger explicit runtime-root override exists and the command runs in project context, the effective runtime root SHALL default to `<active-overlay>/runtime`.
Each cleanup invocation SHALL target exactly one effective runtime root.
Operators who need to clean legacy shared-root artifacts under `~/.houmao/runtime` SHALL do so by supplying an explicit runtime-root override such as `--runtime-root ~/.houmao/runtime`.

#### Scenario: Project-context runtime cleanup targets the overlay-local runtime root by default
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr admin cleanup runtime builds` without `--runtime-root`
- **THEN** the command evaluates build artifacts under `/repo/.houmao/runtime`
- **AND THEN** it does not instead default to a shared runtime root under `~/.houmao/runtime`

#### Scenario: Explicit runtime-root override can still target legacy shared-root cleanup
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr admin cleanup runtime sessions --runtime-root ~/.houmao/runtime`
- **THEN** the command evaluates runtime-session artifacts under `~/.houmao/runtime`
- **AND THEN** it does not also sweep `/repo/.houmao/runtime` in that same invocation
