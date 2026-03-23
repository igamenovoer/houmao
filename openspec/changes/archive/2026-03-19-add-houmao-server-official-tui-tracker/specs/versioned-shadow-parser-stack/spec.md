## ADDED Requirements

### Requirement: Direct tmux-capture integrations can use the shared parser stack without CAO-specific wrappers
The shared parser stack SHALL remain usable for supported TUI snapshots captured directly from tmux by repo-owned integrations.

Its parsing contract SHALL continue to operate on normalized snapshot text plus parser-owned selection context rather than requiring CAO-specific output wrapper types or CAO-specific lifecycle metadata as parser inputs.

#### Scenario: Server-owned direct tmux capture is parsed through the shared stack
- **WHEN** `houmao-server` captures supported live TUI text directly from tmux for a Claude or Codex session
- **THEN** it can submit that captured snapshot to the shared parser stack directly
- **AND THEN** the stack returns the normal structured state, projection, and parser metadata contract without requiring CAO-specific wrapper objects

## MODIFIED Requirements

### Requirement: Repo-owned shadow-aware helper code uses the shared stack-level abstraction
Repo-owned helpers, runtime code, or server integrations that need to parse supported provider TUI snapshots outside the main CAO turn engine SHALL use the shared parser stack or another repo-owned stack-level adapter that preserves provider selection, parser-owned projector selection, controlled override behavior, and structured state/projection outputs.

They SHALL NOT bypass that shared abstraction by pinning provider-private parser classes, CAO provider status helpers, or other ad hoc parser entry points as the normal integration point for server-owned or helper-owned parsing behavior that the stack now owns.

At the `houmao-server` boundary, repo-owned live tracking integrations SHALL treat that shared stack as the official parser for supported live TUI sessions rather than presenting it as a demo-only or shadow-only helper.

#### Scenario: `houmao-server` worker parses supported TUI snapshots through the shared stack
- **WHEN** a `houmao-server` watch worker needs to interpret live Claude or Codex pane content captured directly from tmux
- **THEN** it obtains parsing behavior through the shared parser stack or an equivalent thin repo-owned adapter
- **AND THEN** provider/version-specific parser and projector selection remains centralized behind that shared abstraction

#### Scenario: Server integration does not bypass the shared parser contract
- **WHEN** a repo-owned server integration needs parsed TUI state for a supported live tool
- **THEN** it does not make CAO provider `get_status()` helpers or provider-private parser classes the normal parser entry point
- **AND THEN** the shared stack remains the canonical parser integration boundary for that supported tool
