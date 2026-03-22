## ADDED Requirements

### Requirement: Recorded validation SHALL require successful authoring evidence before a fixture is promoted into the canonical corpus
The recorded validation workflow SHALL be used as a promotion gate for any real tmux-backed fixture that is copied into `tests/fixtures/shared_tui_tracking/recorded/`.

At minimum, the authoring run being promoted SHALL have:

- zero replay mismatches,
- complete label coverage,
- a generated Markdown summary report, and
- a generated review video rendered from the same pane snapshots that feed replay.

#### Scenario: Canonical fixture promotion is blocked until authoring evidence is complete
- **WHEN** a maintainer prepares to promote one temporary real capture into the committed fixture corpus
- **THEN** the recorded-validation workflow has already produced zero-mismatch replay output, a summary report, and a review video for that authoring run
- **AND THEN** the fixture is not considered canonical until those promotion checks pass

## MODIFIED Requirements

### Requirement: Recorded validation SHALL ship an initial multi-tool fixture corpus for critical state transitions
The repository SHALL include an initial recorded fixture corpus for the standalone shared TUI tracker, and the canonical committed version of that corpus SHALL be sourced from real tmux-backed captures authored with the recorded-validation workflow rather than from synthetic hand-authored recorder payloads.

At minimum, the first-wave canonical corpus SHALL contain:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `tui_down_after_active`

Each published canonical fixture SHALL preserve the replay-grade canonical artifact set for that case, including the fixture manifest, pane snapshots, runtime observations, labels, and authoritative input events when present.

#### Scenario: Maintained recorded-validation suite runs against the real first-wave corpus
- **WHEN** a developer runs the maintained recorded-validation test suite
- **THEN** the suite includes a canonical first-wave fixture set spanning both Claude and Codex from real tmux-backed captures
- **AND THEN** that corpus exercises success, interruption, ambiguity, and diagnostics-loss boundaries for the standalone tracker
