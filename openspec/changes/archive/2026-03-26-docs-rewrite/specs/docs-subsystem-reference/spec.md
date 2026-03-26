## ADDED Requirements

### Requirement: Gateway reference rewritten without CAO framing

The gateway reference SHALL document the per-agent FastAPI sidecar: protocol and state model, control surfaces (prompts, interrupts, send-keys), mail operations, health checks, and SQLite persistence. Content SHALL be derived from `gateway_service.py`, `gateway_models.py`, and `gateway_storage.py` docstrings. The docs SHALL NOT frame the gateway as a CAO extension.

#### Scenario: Gateway described as session-owned sidecar

- **WHEN** a reader opens gateway reference docs
- **THEN** the gateway is described as a FastAPI companion process for one runtime-owned session, not as a CAO add-on

#### Scenario: Gateway API surface documented

- **WHEN** the gateway reference documents API endpoints
- **THEN** it covers: control input (POST /v1/requests, POST /v1/control/send-keys), mail operations, health, current instance tracking, and mail notifier

### Requirement: Mailbox reference retains current content with accuracy pass

The mailbox reference SHALL retain the existing 12 doc files with a light accuracy pass: verify that protocol version, message format, filesystem layout, and Stalwart integration descriptions match current `mailbox/` source. Remove any stale CAO references if found.

#### Scenario: Mailbox docs match current protocol

- **WHEN** comparing mailbox reference docs to `mailbox/protocol.py` exports
- **THEN** the documented protocol version, message format, and serialization match the source

### Requirement: TUI tracking reference consolidates scattered content

The TUI tracking reference SHALL consolidate content from `developer/tui-parsing/`, `reference/` scattered files, and `resources/tui-state-tracking/` into `reference/tui-tracking/` with three pages: state model (`TrackedStateSnapshot`, signals, transitions), detector profiles (Claude Code, Codex, registry), and replay engine (`StreamStateReducer`, `replay_timeline()`). Content SHALL be derived from `shared_tui_tracking/` module docstrings.

#### Scenario: State model documented from source

- **WHEN** a reader opens the TUI tracking state-model page
- **THEN** they find `TrackedStateSnapshot` fields, `DetectedTurnSignals`, `CompletionState`, `ProcessState`, `ReadinessState`, `TurnPhase` — all derived from `shared_tui_tracking/models.py`

#### Scenario: Detector profiles documented

- **WHEN** a reader opens the TUI tracking detectors page
- **THEN** they find `ClaudeCodeSignalDetectorV2_1_X`, `CodexTuiSignalDetector`, `DetectorProfileRegistry`, and `app_id_from_tool()` with their detection contracts

### Requirement: Lifecycle completion detection documented

The lifecycle reference SHALL include a page documenting the ReactiveX completion detection pipelines: `TurnAnchor`, `ReadinessSnapshot`, `AnchoredCompletionSnapshot`, `build_readiness_pipeline()`, `build_anchored_completion_pipeline()`. Content SHALL be derived from `lifecycle/` module docstrings.

#### Scenario: Reader understands turn-anchored detection

- **WHEN** a reader opens the completion-detection page
- **THEN** they find the `TurnAnchor` concept, readiness vs completion lifecycle statuses, and how the ReactiveX pipelines compose

### Requirement: Registry reference retains current content with accuracy pass

The registry reference SHALL retain existing content with a light accuracy pass: verify that `ManagedAgentRecord`, `LiveAgentRecord`, and filesystem registry operations match `registry_models.py` and `registry_storage.py` source. Remove any stale CAO references.

#### Scenario: Registry docs match current models

- **WHEN** comparing registry reference docs to `registry_models.py` exports
- **THEN** the documented record fields and operations match the source

### Requirement: Terminal record reference updated

The terminal record reference SHALL document the recording and replay capabilities derived from `terminal_record/` module docstrings, covering tmux session capture and asciinema format support.

#### Scenario: Terminal record docs reflect current capabilities

- **WHEN** a reader opens terminal record reference
- **THEN** they find recording setup, capture format, and replay capability descriptions matching `terminal_record/` source
