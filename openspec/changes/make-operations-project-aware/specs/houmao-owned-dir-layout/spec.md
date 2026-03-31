## MODIFIED Requirements

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different responsibilities while making the active project overlay the default local root for non-registry state.

The default per-user shared Houmao root that remains global SHALL be:
- registry root: `~/.houmao/registry`

For maintained local project-aware command flows, the default overlay-owned roots SHALL be:
- runtime root: `<active-overlay>/runtime`
- mailbox root: `<active-overlay>/mailbox`
- jobs root base: `<active-overlay>/jobs`

For each started session in project-aware local command flows, the default per-agent job dir SHALL be derived as:
- `<active-overlay>/jobs/<session-id>/`

The system SHALL continue to support stronger override surfaces for those locations:
- explicit CLI/config override where supported,
- existing env-var overrides such as `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, and `HOUMAO_LOCAL_JOBS_DIR`.

When both an explicit CLI/config override and an env-var override exist for the same effective location, the explicit override SHALL win.
When no explicit override exists but a supported env-var override is set, the env-var override SHALL win.
When neither explicit override nor env-var override is supplied for a maintained local project-aware flow, the system SHALL use the overlay-derived defaults above.

#### Scenario: Project-aware local roots resolve under the active overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local Houmao launch or build flow starts without stronger root overrides
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root is `/repo/.houmao/mailbox`
- **AND THEN** the effective job-dir base is `/repo/.houmao/jobs`

#### Scenario: Shared registry remains under the user home by default
- **WHEN** an operator runs maintained local Houmao commands in project context without a registry override
- **THEN** the effective shared registry root remains under `~/.houmao/registry`
- **AND THEN** the command does not relocate the registry under the active project overlay by default

#### Scenario: Jobs root env override still relocates per-session job dirs
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `HOUMAO_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** no stronger explicit jobs-root override exists
- **THEN** the effective job dir for a started session is derived under `/tmp/houmao-jobs/<session-id>/`
- **AND THEN** the overlay-local jobs default is not used for that session

### Requirement: Workspace-local scratch behavior is manual-cleanup and documentation-guided in this change
For this change, the system SHALL treat default project-aware job dirs as manually managed scratch space rather than auto-cleaned runtime state.

The default project-aware job-dir family SHALL live under the active overlay as `<active-overlay>/jobs/`.

The system SHALL NOT require auto-generated nested `.gitignore` files under `<active-overlay>/jobs/` as part of this change.

Reference docs for this change SHALL describe overlay-local `jobs/` as local scratch/runtime state that remains operator-managed for cleanup even though it now lives under the active project overlay by default.

#### Scenario: Stop-session leaves the overlay-local job dir in place
- **WHEN** a developer stops a session that used the default project-aware job dir under `<active-overlay>/jobs/<session-id>/`
- **THEN** the runtime leaves that job dir in place in this version
- **AND THEN** cleanup of that scratch directory remains a manual operator action
