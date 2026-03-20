## ADDED Requirements

### Requirement: Interactive watch pack SHALL launch a recorder-backed Claude session from repository brain fixtures with a live dashboard
The repository SHALL provide an interactive Claude state-tracking watch workflow under `scripts/explore/claude-code-state-tracking/` that can build a fresh Claude runtime home from `tests/fixtures/agents/brains/`, launch the generated `launch.sh` in tmux, start recorder-backed observation, and bring up a live dashboard for the same run.

The interactive watch SHALL provide, at minimum:

- a `start` workflow that creates a fresh run root,
- a run-local runtime root under that run root for generated brain artifacts,
- a brain-backed Claude launch path driven by fixture recipes, config profiles, and credential profiles,
- a tmux-backed Claude session for manual prompting,
- a live dashboard process or session,
- terminal-recorder capture in `passive` mode,
- runtime liveness observation, and
- explicit attach information for the Claude session and dashboard.

#### Scenario: Operator starts an interactive watch run
- **WHEN** a developer starts the interactive Claude watch workflow
- **THEN** the workflow builds a fresh Claude runtime home from repository brain fixtures and launches its generated `launch.sh` in tmux together with recorder-backed observation and a live dashboard
- **AND THEN** the generated brain home and manifest live under that run's own runtime subtree rather than a shared global runtime directory
- **AND THEN** the workflow returns the run root and attach points for both the Claude session and the dashboard

### Requirement: Interactive watch SHALL remain independent from Houmao server and session-management CLIs
The interactive watch SHALL remain as independent as practical from `houmao-server` and Houmao session-management CLI workflows.

The watch MAY reuse shared Houmao Python modules for:

- brain-home construction,
- recorder lifecycle,
- tmux helpers,
- detector selection, and
- ReactiveX reducer logic.

The watch SHALL NOT require:

- `houmao-server` routes,
- `houmao-cli` subprocess calls, or
- `houmao.agents.realm_controller` lifecycle subprocess calls such as `build-brain`, `start-session`, `send-prompt`, or `stop-session`.

#### Scenario: Interactive watch builds and launches without Houmao lifecycle CLI subprocesses
- **WHEN** a developer starts the interactive Claude watch workflow
- **THEN** the workflow uses shared Python/library code plus direct tmux and recorder orchestration for its normal lifecycle
- **AND THEN** the workflow does not depend on Houmao server routes or Houmao session-management CLI subprocesses to run

### Requirement: Interactive dashboard SHALL derive live state from recorder/runtime observations using the simplified state model
The interactive dashboard SHALL consume the same recorder pane snapshots and runtime liveness observations that are retained for later analysis, and it SHALL derive live state using the simplified Claude turn model rather than a second ad hoc parser contract.

At minimum, the dashboard SHALL present:

- diagnostics availability,
- turn phase,
- last terminal result,
- accepting-input, editing-input, and ready-posture surface facts,
- active reasons and detector notes,
- observed detector family/version, and
- current sample identity or elapsed time.

#### Scenario: Operator watches live state while prompting Claude manually
- **WHEN** the operator interacts with the live Claude tmux session during an interactive watch run
- **THEN** the dashboard updates from appended recorder/runtime observations rather than an unrelated sampling path
- **AND THEN** the displayed state reflects the simplified model as the visible Claude surface changes

### Requirement: Interactive watch SHALL persist live state samples and transition artifacts
Each interactive run SHALL persist a machine-readable live state stream in addition to the raw recorder artifacts.

At minimum, the run artifacts SHALL include:

- `latest_state.json`,
- `state_samples.ndjson`, and
- `transitions.ndjson`.

The transition artifact SHALL record material public-state changes rather than every raw pane sample.

#### Scenario: Live state artifacts are retained during an interactive run
- **WHEN** an interactive watch run is active
- **THEN** the workflow persists machine-readable current-state and transition artifacts alongside the recorder output
- **AND THEN** a developer can inspect those artifacts without scraping the dashboard terminal manually

### Requirement: Interactive watch SHALL expose run metadata and current state through `inspect`
The interactive pack SHALL provide an `inspect` workflow that exposes the current run metadata and latest known state in a stable machine-readable form.

At minimum, `inspect --json` SHALL include:

- run root,
- run-local runtime root,
- brain home path,
- brain manifest path,
- Claude tmux attach command,
- dashboard attach command,
- recorder root,
- latest state payload, and
- artifact paths for retained live-state streams.

#### Scenario: Operator inspects a live run without attaching to the dashboard
- **WHEN** a developer runs `inspect --json` for an active interactive watch run
- **THEN** the command returns the latest known state together with attach commands and artifact paths
- **AND THEN** the developer can determine the current posture and where the run artifacts are located

### Requirement: Interactive watch SHALL finalize each run with offline analysis and a report
Stopping an interactive watch run SHALL finalize the retained artifacts with the same offline analysis stages used by the scripted harness:

- content-first groundtruth,
- replay tracking,
- comparison, and
- a developer-readable report that explains whether the run passed or failed semantically.

The final report SHALL cite the relevant analysis artifacts when it claims pass/fail status.

#### Scenario: Operator stops an interactive watch run
- **WHEN** a developer stops an interactive watch run
- **THEN** the workflow finalizes groundtruth, replay, and comparison artifacts for that run
- **AND THEN** it writes a report explaining the observed result and whether replay matched the final interpretation

### Requirement: Interactive watch SHALL reuse closest-compatible detector selection and ReactiveX-timed reducer semantics
The interactive watch SHALL use the same closest-compatible detector families and ReactiveX-driven timing semantics as the scripted explore harness for Claude state tracking.

Timed behaviors such as success settle and reset SHALL remain ReactiveX-driven rather than being reimplemented as ad hoc wall-clock bookkeeping inside the dashboard.

#### Scenario: Live dashboard and offline replay follow the same state semantics
- **WHEN** a recorded interactive run is replayed offline after the dashboard already processed it live
- **THEN** both live and offline classification use the same detector family and Rx-timed reducer semantics
- **AND THEN** any mismatch can be investigated as an evidence or logic problem rather than as intentional model drift between live and replay paths

### Requirement: Interactive watch SHALL support artifact-first debugging and optional dense local traces
The interactive watch SHALL be debuggable from retained artifacts first. If retained recorder, runtime, state-sample, and comparison artifacts are insufficient, the workflow MAY enable an env-gated dense trace mode for local detector/reducer debugging.

Any dense trace mode SHALL be optional and local to the interactive watch workflow.

#### Scenario: Developer debugs an unexpected interactive state transition
- **WHEN** a developer finds that the dashboard state during an interactive run looks wrong
- **THEN** the workflow retains enough raw and derived artifacts to investigate the issue without guessing
- **AND THEN** an optional local trace mode can be enabled if those retained artifacts still do not explain the mismatch
