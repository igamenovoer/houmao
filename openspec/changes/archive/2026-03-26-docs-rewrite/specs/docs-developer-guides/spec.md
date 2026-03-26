## ADDED Requirements

### Requirement: TUI parsing developer guide rewritten without CAO transport framing

The `developer/tui-parsing/` guide SHALL be rewritten to describe the TUI parsing stack in terms of current abstractions: `StreamStateReducer`, detector profiles from `DetectorProfileRegistry`, signal contracts per tool, and the `shared_tui_tracking` package. All references to "CAO transport surface" or "CAO terminal" as primary framing SHALL be replaced with the actual execution contexts (tmux panes for `local_interactive`, process stdout for headless).

#### Scenario: Architecture page describes actual execution contexts

- **WHEN** a reader opens `developer/tui-parsing/architecture.md`
- **THEN** the architecture is framed around tmux pane capture and headless stdout, not around "CAO transport surface"

#### Scenario: Maintenance guide references current packages

- **WHEN** a reader opens `developer/tui-parsing/maintenance.md`
- **THEN** maintenance procedures reference `shared_tui_tracking/` detectors and `shared_tui_tracking/apps/` for per-tool signal profiles

### Requirement: Terminal record developer guide updated

The `developer/terminal-record/` guide SHALL be updated to remove any CAO references and ensure the architecture, recording workflow, and maintenance procedures match the current `terminal_record/` source.

#### Scenario: Terminal record guide reflects current implementation

- **WHEN** a reader opens terminal record developer docs
- **THEN** the content describes tmux-backed recording without CAO dependencies

### Requirement: Houmao-server developer guide rewritten

The `developer/houmao-server/` guide SHALL be rewritten to describe the server internals (FastAPI app factory, service orchestration, managed agent tracking, gateway proxying) derived from `server/` module docstrings. CAO child process supervision SHALL be mentioned only as a legacy compatibility feature.

#### Scenario: Server internals documented from source

- **WHEN** a reader opens houmao-server developer docs
- **THEN** they find `create_app()` factory, `HoumaoServerService` orchestration, managed agent tracking, and gateway proxy descriptions derived from source
