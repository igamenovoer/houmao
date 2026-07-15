# TUI Pending State Capture Runner Specification

## Purpose
Defines the tracker-blind tmux capture workflow used to collect, label, review, and freeze provider pending-message lifecycle evidence.

## Requirements

### Requirement: Runner launches an unattended provider session
The runner SHALL accept a provider (`claude`, `codex`, or `kimi`) and a fresh run root, then launch an unattended managed agent with an isolated provider home and a Boltons fixture copy.

#### Scenario: Launch a Codex capture
- **WHEN** the operator invokes the runner with `--provider codex --run-root tmp/houmao-dev-testing/20260714-codex-pending`
- **THEN** the runner creates the run root, copies the Boltons fixture, and starts an unattended Codex tmux session

### Requirement: Runner captures 20 Hz pane snapshots and input events
The runner SHALL start an active terminal recording at `0.05` s intervals before the first lifecycle input and stop it after the final settled ready hold, producing `pane_snapshots.ndjson`, `input_events.ndjson`, and `session.cast`.

#### Scenario: Canonical recording authority
- **WHEN** the runner completes a lifecycle
- **THEN** `capture/recording/pane_snapshots.ndjson` exists and contains one row per `0.05` s sample captured while the tmux pane was visible

### Requirement: Runner executes the prompt-queue lifecycle
The runner SHALL execute the sequence `ready → first_prompt → processing → second_prompt → pending → dequeue → processing → done → ready` using tmux `send_text` and `send_key` actions, fixed waits, and visible-pattern waits.

#### Scenario: Second prompt is submitted while processing
- **WHEN** the visible surface matches the provider-specific active-turn pattern
- **THEN** the runner injects the second prompt text into the tmux pane followed by `Enter`

#### Scenario: Pending state is observed
- **WHEN** the visible surface matches the provider-specific pending-message pattern
- **THEN** the runner records the elapsed time of the first pending sample and continues holding until the pending signature disappears

### Requirement: Runner execution is tracker-blind
During canonical capture, the runner SHALL decide step timing using only fixed waits (`wait_seconds`) or direct visible-pattern waits (`wait_for_pattern`). It SHALL NOT use `wait_for_ready`, `wait_for_active`, or any detector-backed gate.

#### Scenario: Wait for visible active signature
- **WHEN** a lifecycle step declares `wait_for_pattern` with pattern `"Working ("`
- **THEN** the runner polls the latest pane snapshot for that pattern and proceeds only when it appears, without consulting the tracker

### Requirement: Runner assigns binary labels automatically from snapshots
After the recording is frozen, the runner SHALL analyze `pane_snapshots.ndjson` and emit `labels/labels.json` with one row per source sample containing exactly `can_accept_input` and `has_pending_message`, each with values `yes`, `no`, or `unknown`, plus an `evidence_note`. The analyzer SHALL use the same provider-specific patterns that drove the lifecycle (ready cue, active-turn cue, pending-message cue) and MAY process snapshots in batches.

#### Scenario: Ready span labeled automatically
- **WHEN** a sample matches the ready cue and does not match active-turn or pending-message cues
- **THEN** the analyzer labels it `can_accept_input=yes` and `has_pending_message=no`

#### Scenario: Pending span labeled automatically
- **WHEN** a sample matches the active-turn cue and the pending-message cue
- **THEN** the analyzer labels it `can_accept_input=no` and `has_pending_message=yes`

### Requirement: Runner renders a labeled review video
The runner SHALL render an MP4 video from the labeled snapshots that shows the tmux pane content plus an overlay with `can_accept_input` and `has_pending_message` for each frame, so a human can audit the automated labels without reading raw `ndjson`.

#### Scenario: Human checks the labeled video
- **WHEN** the operator opens `review/labels.mp4`
- **THEN** each frame displays the terminal content and the two binary labels with the sample timestamp and evidence note

### Requirement: Label file contains only the two binary targets
The label file SHALL contain exactly `can_accept_input` and `has_pending_message` plus an `evidence_note`. It SHALL NOT include the seven public tracked-state fields.

#### Scenario: Label schema audit
- **WHEN** a downstream consumer reads `labels/labels.json`
- **THEN** each row has only `can_accept_input`, `has_pending_message`, and `evidence_note`

### Requirement: Runner freezes source evidence
After the recorder stops, the runner SHALL compute SHA-256 digests of the recorder manifest, `pane_snapshots.ndjson`, `input_events.ndjson`, `session.cast`, the lifecycle manifest, and the label template, then write them to `capture/frozen-evidence.json`.

#### Scenario: Evidence immutability gate
- **WHEN** the runner finishes a successful capture
- **THEN** `capture/frozen-evidence.json` exists and references the exact byte digests of the source artifacts

### Requirement: Runner preserves failed and tainted attempts
If any step fails, an unallowlisted confirmation appears, or a required pattern never appears, the runner SHALL stop execution, record `run_tainted` reasons, still run the freeze gate, and exit non-zero.

#### Scenario: Lifecycle does not reach pending state
- **WHEN** the provider does not show a visible pending-message signature after the second prompt
- **THEN** the runner marks the attempt tainted with `unsupported_pending_behavior`, preserves the recording, and exits non-zero

### Requirement: Runner cleans up transient resources
The runner SHALL remove copied credentials, isolated provider homes, and demo-owned tmux sessions after capture, while preserving the recording, manifests, label template, and any taint records.

#### Scenario: Cleanup after a failed Kimi attempt
- **WHEN** a Kimi capture fails because the provider exits unexpectedly
- **THEN** the provider home and tmux session are removed, but `capture/recording/` and `labels/labels.json` remain

### Requirement: Runner does not modify source code
The runner SHALL be implemented entirely under `scripts/qualification/tui-prompt-admission/`. It may import public helpers from `src/houmao/` but SHALL NOT edit any tracker, demo-pack, gateway, or CLI source files.

#### Scenario: Scope audit after implementation
- **WHEN** the change is finalized
- **THEN** `git diff --name-only` shows no paths under `src/houmao/`
