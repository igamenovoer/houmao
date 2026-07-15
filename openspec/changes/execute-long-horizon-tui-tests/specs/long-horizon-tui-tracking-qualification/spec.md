## ADDED Requirements

### Requirement: Fixed Provider and Procedure Matrix
The qualification workflow SHALL derive its session catalog from UC-02 and SHALL execute Claude on ST-01 through ST-04, Codex on ST-01 through ST-05, and Kimi on ST-03 through ST-05. A complete qualification run SHALL therefore contain 12 distinct provider/procedure cells and 242 recorded user operations: 20 operations for every ST-01 through ST-04 cell and 21 operations for every ST-05 cell. Gemini CLI MUST NOT appear in the catalog, launch adapters, credential resolution, artifacts, or reports.

#### Scenario: Planner expands the complete matrix
- **WHEN** the operator asks the workflow to plan a complete UC-02 qualification run
- **THEN** the plan contains exactly the 12 declared provider/procedure cells and exactly 242 uniquely identified user operations
- **THEN** each operation preserves the exact prompt or semantic action, engineering checkpoint, and tracker checkpoint declared by UC-02

#### Scenario: Partial selection cannot pass the suite
- **WHEN** the operator selects one provider or procedure for diagnostic execution
- **THEN** the workflow marks the aggregate run incomplete and does not issue a suite-level pass

### Requirement: Owned Temporary Run Root
The workflow SHALL require one run root that resolves beneath the repository-local `tmp/` directory and SHALL keep every copied project, isolated provider home, runtime file, recording, label, replay artifact, log, diff, failure slice, and report beneath that root. The workflow MUST reject absolute or relative paths that resolve outside `tmp/`, symlink escapes, reuse of an unowned non-empty directory, and cleanup requests for resources without matching ownership metadata.

#### Scenario: Caller selects a valid temporary root
- **WHEN** the caller passes `tmp/tui-state-tracking-long-horizon/example-run`
- **THEN** the workflow records the resolved root and ownership marker before creating session resources
- **THEN** all subsequently declared output paths remain descendants of that root

#### Scenario: Caller selects an unsafe root
- **WHEN** a requested root or one of its existing ancestors resolves outside the repository-local `tmp/` directory
- **THEN** the workflow stops before launch with `unsafe_mutation_scope` and does not create, mutate, or delete the target

### Requirement: Immutable Boltons Session Projects
The workflow SHALL treat `tests/fixtures/test-projects/boltons` as immutable input and SHALL prepare a fresh copied project for every provider/procedure cell. Preparation MUST verify upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe`, record a cache-excluding SHA-256 tree digest, remove generated caches only from the copy, initialize a fresh Git repository with run-local identity, create a `houmao-baseline` commit, and confirm that the managed Python environment collects exactly 437 tests without network access or package installation.

#### Scenario: Session project passes preflight
- **WHEN** the source revision, source digest, copied tree, baseline commit, initial clean status, and 437-test collection check all succeed
- **THEN** the workflow records those facts in the session project manifest and permits provider launch in the copied project

#### Scenario: Fixture preflight differs
- **WHEN** the revision, source digest, initial status, or collection count differs from the pinned contract
- **THEN** the workflow records `fixture_preflight_failed`, skips provider launch, and leaves the vendored fixture unchanged

#### Scenario: Source fixture changes during a run
- **WHEN** the post-run digest of the vendored fixture differs from the preflight digest
- **THEN** the aggregate run fails `unsafe_mutation_scope` even if every tracker comparison passed

### Requirement: Exact Operation Expansion and Authoritative Input Log
The workflow SHALL load checked-in, machine-readable ST-01 through ST-05 definitions that retain a verifiable link and content digest for the UC-02 source document. It SHALL expand only `{{SAFE}}`, `{{PLACEHOLDER_LITERAL}}`, `{{PANE}}`, and `{{LAUNCH_COMMAND}}`, validate provider-specific values before capture, and persist every fully expanded prompt or exact key/control sequence as one uniquely identified semantic input event with timestamps and checkpoint references. It MUST NOT improvise recovery prompts, navigation actions, exit actions, or substitutions during a recorded attempt.

#### Scenario: Exact prompt is submitted
- **WHEN** an operation declares a submitted prompt containing `{{SAFE}}`
- **THEN** the input log contains the complete literal safety prefix and prompt followed by one recorded `Enter` action
- **THEN** no undeclared template token remains in the expanded operation

#### Scenario: Procedure drifts from its source
- **WHEN** a checked-in procedure digest or operation catalog no longer matches the reviewed UC-02 source contract
- **THEN** planning fails before any project or provider resource is created

#### Scenario: Engineering checkpoint fails
- **WHEN** a provider response or project state does not satisfy an operation's engineering checkpoint
- **THEN** the attempt receives `scenario_task_divergence`, no corrective prompt is sent, and the attempt is excluded from tracker qualification

### Requirement: Maintained Unattended Provider Launch
Every live session SHALL use the maintained `unattended` launch-policy strategy for its declared Claude, Codex, or Kimi version and SHALL start in the run-local copied project with an isolated provider home. The preflight SHALL reject confirmation, approval, permission, trust, login, update, session-picker, browser, or model-generated user-question surfaces unless a version-scoped allowlist proves an unavoidable hard-coded intervention with no supported bypass. Codex sessions SHALL project the required proxy through `127.0.0.1:7990` and SHALL fail preflight rather than silently launching without a reachable proxy.

#### Scenario: Provider is ready without intervention
- **WHEN** a maintained provider version resolves an unattended strategy, its credentials are ready, required provider-specific probes pass, and the TUI reaches prompt-free readiness
- **THEN** the workflow records the version, strategy identifier, sanitized launch environment, launch command digest, pane target, and readiness evidence before capture

#### Scenario: Codex proxy is unavailable
- **WHEN** port 7990 is unreachable or the Codex launch environment does not contain the required proxy projection
- **THEN** the Codex cell stops with `provider_preflight_failed` before the operation catalog begins

#### Scenario: Unattended posture requests confirmation
- **WHEN** an unallowlisted intervention surface appears during preflight or capture
- **THEN** the workflow stops normal operations, records `unattended_confirmation_violation`, and retains the evidence span

#### Scenario: Provider interaction surface is unsupported
- **WHEN** the exact steering, `/model Enter`, or empty-editor `Ctrl+D` behavior required by a procedure is unsupported by the maintained provider version
- **THEN** the cell is marked with its declared unsupported-surface result and no substitute action is attempted

### Requirement: Resumable Phase Boundary and Blind Labeling
The workflow SHALL persist an idempotent phase state machine covering plan, preflight, capture, manual labeling, replay, and aggregate reporting for every matrix cell. Capture SHALL complete and freeze its authoritative recording before the manual-label phase begins. Human labelers MUST NOT receive tracker predictions, tracker timelines, or comparison output until the label set is explicitly marked complete and its digest is recorded.

#### Scenario: Capture pauses for labels
- **WHEN** a cell completes capture and project checkpoint validation
- **THEN** its phase becomes `awaiting_manual_labels`, its recording is immutable, and replay or tracker comparison remains unavailable

#### Scenario: Operator resumes after labeling
- **WHEN** the operator supplies a schema-valid label set for the frozen recording and marks it complete
- **THEN** the workflow records the label digest and permits replay without repeating successful preflight or capture phases

#### Scenario: Interrupted phase resumes
- **WHEN** the workflow restarts after a process failure
- **THEN** it reads the persisted phase state, verifies completed artifact digests, and resumes at the first incomplete phase without overwriting valid evidence

### Requirement: Canonical High-Frequency Capture
Every qualifying live attempt SHALL record the ordinary provider TUI, authoritative managed input, pane snapshots, terminal cast, runtime observations, and actual timestamps at a requested sample interval of `0.05` seconds. One provider session, tmux pane, recorder, tracker context, and copied project SHALL remain stable throughout a procedure except for the explicit in-pane provider restart in ST-05. Tracker output MUST NOT serve as recording ground truth.

#### Scenario: Complete canonical recording
- **WHEN** the recorder captures the full operation span with authoritative timestamps and no required transition gap
- **THEN** the workflow freezes a replay-compatible recording manifest and advances the cell to manual labeling

#### Scenario: Recorder misses required evidence
- **WHEN** the recording omits the complete span for a required transition or loses input authority
- **THEN** the attempt is incomplete and MUST be rerun unchanged from a fresh copied project

### Requirement: Canonical and Delayed-Cadence Replay
The workflow SHALL validate every labeled recording using strict sample-aligned canonical replay and fixed 10 Hz, 5 Hz, and 2 Hz derived schedules at zero and half-interval phase offsets. It SHALL also run seeded jitter, isolated-gap, and burst schedules when the replay derivation interface supports them, and otherwise record `not_run_capability_missing`. Every derived observation SHALL retain its mapping to authoritative source samples and timestamps.

#### Scenario: Canonical replay matches labels
- **WHEN** the tracker replays the frozen high-frequency stream against completed manual labels
- **THEN** the cell records zero unexplained public-state mismatches for a canonical pass

#### Scenario: Delayed capture omits a transient state
- **WHEN** a 10 Hz, 5 Hz, or 2 Hz replay legitimately skips a short-lived manually labeled state
- **THEN** the semantic oracle permits the omission only if the timeline remains safe, ordered, turn-correct, and free of fabricated terminal outcomes or stale authority

#### Scenario: Derived cadence violates safety
- **WHEN** any fixed-rate replay at 2 Hz or faster fabricates a result, reverses active and terminal order, retains readiness through liveness loss, or associates an outcome with the wrong turn
- **THEN** the tracker verdict fails and preserves the smallest mapped source-sample evidence slice

### Requirement: Separate Engineering and Tracker Verdicts
The workflow SHALL produce independent engineering and tracker verdicts for every attempt. Engineering evaluation SHALL cover exact prompts, project checkpoints, mutation scope, command results, provider behavior, and procedure completeness. Tracker evaluation SHALL cover label comparison, public-state transitions, state authority, liveness, downstream schema admission, transition-index monotonicity, and terminal-outcome uniqueness. A failure in one verdict MUST NOT be relabeled as a failure in the other.

#### Scenario: Provider completes the wrong task safely
- **WHEN** visible state tracking remains coherent but a required project or response checkpoint fails
- **THEN** engineering reports `scenario_task_divergence` and tracker qualification remains `not_qualified`

#### Scenario: Project task succeeds but tracking diverges
- **WHEN** engineering checkpoints pass but canonical replay disagrees with manual labels or violates a tracker invariant
- **THEN** engineering reports pass and tracker reports failure with the first-divergence slice

#### Scenario: Scheduled active stimulus ends early
- **WHEN** a turn settles before its declared steering or interruption checkpoint
- **THEN** engineering reports `stimulus_too_short` and the unchanged procedure requires a fresh attempt

### Requirement: Procedure Mutation and Final-State Contracts
The workflow SHALL compare every copied project with `houmao-baseline` after capture. ST-01, ST-02, and ST-04 SHALL finish clean; ST-03 SHALL change only `tests/test_houmao_long_horizon.py` and `docs/houmao-long-horizon.rst`; and ST-05 SHALL add only `houmao_artifacts/st05.txt`. Network access, package installation, or changes to dependency and project configuration files SHALL fail the attempt.

#### Scenario: Final project diff is allowed
- **WHEN** the final status and diff match the exact procedure-specific path and content contract
- **THEN** the engineering verdict records the diff digest and permits tracker qualification

#### Scenario: Agent changes an undeclared path
- **WHEN** the final status, live mutation watchdog, or checkpoint detects an undeclared project path or forbidden configuration change
- **THEN** the workflow stops with `unsafe_mutation_scope` and retains the causal operation and project evidence

### Requirement: Aggregate Qualification Report
The workflow SHALL produce machine-readable and Markdown aggregate reports containing matrix completeness, provider and strategy versions, operation counts, fixture and prompt digests, engineering verdicts, tracker verdicts, transition-family coverage, cadence results, intervention results, resource use, artifact inventory, and retained issue slices. The suite SHALL pass only when all 12 cells qualify, all 242 operations complete, every declared transition family is covered, every canonical replay has zero unexplained mismatch, every fixed replay at 2 Hz or faster has zero safety violation, and all unattended, source-integrity, mutation, cleanup, and downstream-consumer invariants pass.

#### Scenario: Full matrix passes
- **WHEN** every required cell and operation satisfies all engineering, tracker, cadence, safety, and integrity gates
- **THEN** the report issues a suite-level pass and links every result to its immutable evidence artifacts

#### Scenario: Cell is missing, unsupported, or quarantined
- **WHEN** any required cell is incomplete, unsupported, awaiting labels, excluded for provider/network failure, or otherwise not qualified
- **THEN** the report issues no suite-level pass and states the exact missing obligation

### Requirement: Hermetic Tests and Explicit Live Execution
Planner, schema, path-ownership, prompt-expansion, matrix-completeness, phase-resume, fixture-copy, replay-oracle, and report-aggregation behavior SHALL have deterministic tests that require no provider credentials or network access. Real Claude, Codex, and Kimi qualification SHALL run only through an explicit manual or integration command and SHALL never become part of the default unit-test command.

#### Scenario: Unit test suite exercises orchestration
- **WHEN** developers run the hermetic qualification tests
- **THEN** fake recordings, providers, clocks, and project checkpoints cover success, resume, unsafe-path, confirmation, divergence, cadence, and incomplete-matrix outcomes without reading live credentials

#### Scenario: Operator requests live qualification
- **WHEN** the operator explicitly starts a live matrix or cell under a selected `tmp/<subdir>` run root
- **THEN** the workflow performs provider and credential preflight before spending operations and records that the run used live external model services

### Requirement: Secret-Safe Retention and Owned Cleanup
Artifacts SHALL omit credential values, proxy credentials, access tokens, complete provider-home contents, and unsanitized process environments. Runtime cleanup SHALL stop only tmux sessions and processes named in ownership manifests. Filesystem evidence SHALL remain available by default; explicit deletion SHALL be limited to verified descendants of the selected run root and SHALL record the retained or deleted inventory.

#### Scenario: Reports serialize launch context
- **WHEN** the workflow writes provider or environment metadata
- **THEN** it stores only allowlisted non-secret fields and stable digests for sensitive launch material

#### Scenario: Cleanup encounters an unowned resource
- **WHEN** a process, tmux target, provider home, or directory lacks matching run ownership metadata
- **THEN** cleanup refuses to mutate it and records `unsafe_mutation_scope`
