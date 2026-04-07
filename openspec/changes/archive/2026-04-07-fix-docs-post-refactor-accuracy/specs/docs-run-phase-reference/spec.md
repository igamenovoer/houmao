## MODIFIED Requirements

### Requirement: Role injection documented per backend

The role injection reference SHALL document each backend's injection method and explain the rationale for per-backend differences.

The `RoleInjectionMethod` enumeration in the docs SHALL use the literal values from the code type: `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`. The docs SHALL NOT use the stale name `profile_based`.

The per-backend strategy table and Mermaid diagram SHALL use `cao_profile` for the `cao_rest` and `houmao_server_rest` backends.

#### Scenario: Reader understands why role injection differs by backend
- **WHEN** a reader checks the role injection reference
- **THEN** each backend's injection method is explained with rationale

#### Scenario: Reader sees correct RoleInjectionMethod values
- **WHEN** a reader checks the `RoleInjectionMethod` enumeration in the role injection reference
- **THEN** the listed values are `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`
- **AND THEN** the name `profile_based` does not appear anywhere on the page

### Requirement: Backend model documented with per-backend notes

The backends reference SHALL document the `BackendKind` literal type and per-backend notes.

When the launch policy reference mentions launch surfaces, it SHALL clarify the relationship between `LaunchSurface` (build-phase type that includes `raw_launch`) and `BackendKind` (run-phase type that uses `local_interactive`). The docs SHALL note that `raw_launch` in the build-phase surface maps to `local_interactive` at runtime.

#### Scenario: local_interactive presented as primary
- **WHEN** a reader checks the backend model reference
- **THEN** `local_interactive` is presented as the primary local backend

#### Scenario: Legacy backends reflect current operator posture
- **WHEN** a reader checks the backend model reference for `cao_rest` and `houmao_server_rest`
- **THEN** those backends are positioned as legacy

#### Scenario: Backend selection logic explained
- **WHEN** a reader checks the backend model reference
- **THEN** the backend selection logic is explained

#### Scenario: Launch surface vs backend kind distinction clarified
- **WHEN** a reader checks the launch policy reference for backend surface examples
- **THEN** the page explains that `LaunchSurface` includes `raw_launch` while `BackendKind` uses `local_interactive`
- **AND THEN** the page notes that `raw_launch` maps to `local_interactive` at runtime
