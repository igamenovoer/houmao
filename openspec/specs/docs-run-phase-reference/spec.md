# docs-run-phase-reference Specification

## Purpose
Define the documentation requirements for Houmao run-phase reference content.

## Requirements

### Requirement: LaunchPlan composition documented

The run-phase reference SHALL include a page documenting `LaunchPlan` composition: how `build_launch_plan()` takes a `LaunchPlanRequest` (brain_manifest + role_package + backend + working_directory) and produces a `LaunchPlan` with backend-specific launch arguments. Content SHALL be derived from `launch_plan.py` docstrings.

The page SHALL state that the brain manifest carries launch-profile-derived inputs into runtime launch resolution when the launch originated from a reusable launch profile, including:

- effective auth selection,
- operator prompt-mode intent,
- durable non-secret env records,
- declarative mailbox configuration,
- managed-agent identity defaults,
- prompt-overlay-composed effective role prompt.

The page SHALL state that the build manifest and runtime launch metadata preserve secret-free launch-profile provenance sufficient for inspection and replay, including whether the birth-time config came from an easy profile or an explicit launch profile, and the originating profile name when available.

The page SHALL state that runtime `LaunchPlan` is derived and ephemeral and SHALL NOT be presented as a user-authored object.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model that ties launch profiles to the run-phase composition pipeline.

#### Scenario: Reader understands launch plan resolution

- **WHEN** a reader opens the launch-plan page
- **THEN** they find the `LaunchPlanRequest` fields, the resolution logic (env vars, launch overrides, mailbox bindings, role injection), and the resulting `LaunchPlan` structure

#### Scenario: Reader understands how launch-profile inputs flow into runtime launch resolution

- **WHEN** a reader opens the launch-plan page and looks at how a launch-profile-backed launch is resolved
- **THEN** the page explains that auth selection, operator prompt-mode intent, durable env records, declarative mailbox configuration, managed-agent identity defaults, and the prompt-overlay-composed effective role prompt come through the manifest from the originating launch profile
- **AND THEN** the page explains that launch-profile provenance is preserved in secret-free form on the build manifest and runtime launch metadata

### Requirement: Session lifecycle documented

The run-phase reference SHALL include a page documenting `RuntimeSessionController` and the session lifecycle using the current `start_runtime_session()` and `resume_runtime_session()` behavior derived from `runtime.py`.

That page SHALL describe:

- current start and resume inputs at the level needed for reader understanding,
- session manifest persistence under the runtime-owned session root,
- the distinction between the runtime-owned session root and the workspace-local `job_dir`,
- current lifecycle actions such as prompt delivery, interrupt, raw control input when supported, and stop behavior.

#### Scenario: Reader understands session-root versus job-dir state

- **WHEN** a reader opens the session-lifecycle page
- **THEN** they find that the persisted session manifest lives under the runtime-owned session root
- **AND THEN** the page explains that the workspace-local `job_dir` is a separate per-session scratch or output location rather than the root of authoritative runtime state

#### Scenario: Reader sees current lifecycle behavior rather than stale signatures

- **WHEN** a reader uses the session-lifecycle page to understand start and resume behavior
- **THEN** the page reflects the current runtime lifecycle surfaces and current persistence model
- **AND THEN** it does not describe outdated function signatures or job-dir manifest placement as the current implementation

### Requirement: Backend model documented with per-backend notes

The run-phase reference SHALL include a page documenting the `BackendKind` type and each backend implementation with the current public posture: `local_interactive` as primary, native headless backends as direct CLI alternatives, and `cao_rest` plus `houmao_server_rest` as legacy or compatibility paths. Content SHALL be derived from `models.py` and per-backend module docstrings.

The backend reference SHALL explicitly distinguish between implemented backend existence and recommended operator usage.

When the launch policy reference mentions launch surfaces, it SHALL clarify the relationship between `LaunchSurface` (build-phase type that includes `raw_launch`) and `BackendKind` (run-phase type that uses `local_interactive`). The docs SHALL note that `raw_launch` in the build-phase surface maps to `local_interactive` at runtime.

#### Scenario: local_interactive presented as primary

- **WHEN** a reader opens the backends page
- **THEN** `local_interactive` is the first and most detailed backend described, with headless backends next, and CAO-backed backends last with a "legacy" label

#### Scenario: Legacy backends reflect current operator posture

- **WHEN** the backends page describes `cao_rest` and `houmao_server_rest`
- **THEN** it makes clear that standalone `cao_rest` operator workflows are retired and that those backends remain legacy or compatibility-oriented runtime paths
- **AND THEN** the page does not describe them as the primary recommended backend choice for new operator workflows

#### Scenario: Backend selection logic explained

- **WHEN** the backends page describes backend resolution
- **THEN** it explains `backend_for_tool()` mapping and how `LaunchPlan.backend` is determined

#### Scenario: Launch surface vs backend kind distinction clarified

- **WHEN** a reader checks the launch policy reference for backend surface examples
- **THEN** the page explains that `LaunchSurface` includes `raw_launch` while `BackendKind` uses `local_interactive`
- **AND THEN** the page notes that `raw_launch` maps to `local_interactive` at runtime

### Requirement: Role injection documented per backend

The run-phase reference SHALL include a page documenting role injection: how `plan_role_injection()` produces a `RoleInjectionPlan` with backend-specific strategies. The reference SHALL explain the rationale for per-backend differences.

The `RoleInjectionMethod` enumeration in the docs SHALL use the literal values from the code type: `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`. The docs SHALL NOT use the stale name `profile_based`.

The per-backend strategy table and Mermaid diagram SHALL use `cao_profile` for the `cao_rest` and `houmao_server_rest` backends.

#### Scenario: Reader understands why role injection differs by backend

- **WHEN** a reader opens the role-injection page
- **THEN** they find a table or list mapping each backend to its injection method with a rationale for the difference

#### Scenario: Reader sees correct RoleInjectionMethod values

- **WHEN** a reader checks the `RoleInjectionMethod` enumeration in the role injection reference
- **THEN** the listed values are `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`
- **AND THEN** the name `profile_based` does not appear anywhere on the page

### Requirement: Legacy backend documentation carries an unmaintained deprecation banner

Any run-phase reference page that describes the `cao_rest` or `houmao_server_rest` backends SHALL open the relevant section with a prominent, bold-prefixed deprecation banner identifying the content as unmaintained and possibly incorrect.

At minimum, `docs/reference/realm_controller.md` SHALL include such a banner immediately before the descriptive content for `cao_rest` and immediately before the descriptive content for `houmao_server_rest`. The same banner SHALL appear on `docs/reference/codex-cao-approval-prompt-troubleshooting.md` after it is moved out of the retired agents subtree.

The banner SHALL state, at a minimum:

- that the backend remains in the codebase as a legacy escape hatch,
- that the documentation is no longer actively maintained,
- that the content below may be incorrect or stale,
- and that readers should prefer the current maintained backends (for example `local_interactive`) for new work.

The banner SHALL appear before any descriptive prose, option tables, or workflow diagrams for the deprecated backend. Inline mentions of `cao_rest` or `houmao_server_rest` in lists or tables (for example a backend enumeration) do not by themselves require the banner — only dedicated sections that describe how to use, configure, or troubleshoot the backend trigger the banner requirement.

#### Scenario: Reader opens the realm_controller reference page and reaches the cao_rest section

- **WHEN** a reader scrolls to the `cao_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the realm_controller reference page and reaches the houmao_server_rest section

- **WHEN** a reader scrolls to the `houmao_server_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the moved codex CAO approval troubleshooting page

- **WHEN** a reader opens `docs/reference/codex-cao-approval-prompt-troubleshooting.md`
- **THEN** a bold-prefixed deprecation banner appears at the top of the page
- **AND THEN** the banner states the content is retained only as historical troubleshooting for the deprecated `cao_rest` backend and may be incorrect
