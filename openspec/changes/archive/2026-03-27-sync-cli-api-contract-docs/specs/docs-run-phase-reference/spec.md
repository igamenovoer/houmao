## MODIFIED Requirements

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

The run-phase reference SHALL include a page documenting the `BackendKind` type and each backend implementation with the current public posture: `local_interactive` as primary, native headless backends as direct CLI alternatives, and `cao_rest` plus `houmao_server_rest` as legacy or compatibility paths.

The backend reference SHALL explicitly distinguish between implemented backend existence and recommended operator usage.

#### Scenario: local_interactive presented as primary

- **WHEN** a reader opens the backends page
- **THEN** `local_interactive` is the first and most detailed backend described, with headless backends next, and legacy backends last with a clear legacy label

#### Scenario: Legacy backends reflect current operator posture

- **WHEN** the backends page describes `cao_rest` and `houmao_server_rest`
- **THEN** it makes clear that standalone `cao_rest` operator workflows are retired and that those backends remain legacy or compatibility-oriented runtime paths
- **AND THEN** the page does not describe them as the primary recommended backend choice for new operator workflows
