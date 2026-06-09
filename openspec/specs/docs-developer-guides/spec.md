# docs-developer-guides Specification

## Purpose
Define the documentation requirements for Houmao developer guides.

## Requirements

### Requirement: TUI parsing developer guide rewritten without CAO transport framing

The `developer/tui-parsing/` guide SHALL be rewritten to describe the runtime-owned TUI parsing stack in terms of current abstractions: `StreamStateReducer`, detector profiles from `DetectorProfileRegistry`, signal contracts per tool, and the `shared_tui_tracking` package. All references to "CAO transport surface" or "CAO terminal" as primary framing SHALL be replaced with the actual execution contexts (tmux panes for `local_interactive`, process stdout for headless).

The guide SHALL explicitly state that Claude Code, Codex, and Kimi Code have maintained local-interactive TUI tracking coverage. The architecture page's compact provider-parser or detector-profile diagrams SHALL include Kimi when they list three maintained TUI providers.

The guide SHALL explicitly state that Gemini is lower-priority for TUI parsing because maintained Gemini integration is headless-oriented for TUI tracking documentation. The index page SHALL include a provider note explaining that Claude, Codex, and Kimi have maintained local-interactive TUI tracking profiles while Gemini remains outside the maintained TUI tracking path by default. The shared-contracts page SHALL note that legacy `ShadowParserStack` provider subclasses cover Claude and Codex, while Kimi uses a dedicated shared-tracker detector profile rather than routing through that legacy parser stack.

#### Scenario: Architecture page describes actual execution contexts

- **WHEN** a reader opens `developer/tui-parsing/architecture.md`
- **THEN** the architecture is framed around tmux pane capture and headless stdout, not around "CAO transport surface"

#### Scenario: Maintenance guide references current packages

- **WHEN** a reader opens `developer/tui-parsing/maintenance.md`
- **THEN** maintenance procedures reference `shared_tui_tracking/` detectors and `shared_tui_tracking/apps/` for per-tool signal profiles

#### Scenario: Reader sees Kimi as maintained TUI tracking coverage

- **WHEN** a reader checks the TUI parsing index page
- **THEN** the page presents Claude Code, Codex, and Kimi Code as maintained local-interactive TUI tracking coverage
- **AND THEN** Kimi does not appear only as an unsupported-tool fallback or future note

#### Scenario: Reader understands Gemini TUI tracking posture

- **WHEN** a reader checks the TUI parsing index page
- **THEN** the page explains that Gemini remains outside the maintained TUI tracking path by default
- **AND THEN** the shared-contracts page distinguishes Claude and Codex legacy parser subclasses from Kimi's dedicated shared-tracker detector profile

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
