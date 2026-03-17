# mailbox-roundtrip-shadow-only-automation Specification

## Purpose
TBD - created by archiving change enforce-shadow-only-mailbox-roundtrip-automation. Update Purpose after archive.

## Requirements

### Requirement: Automatic CAO-backed mailbox roundtrip coverage uses `shadow_only` for both participants
The automatic CAO-backed mailbox roundtrip workflow for `scripts/demo/mailbox-roundtrip-tutorial-pack` SHALL resolve `parsing_mode=shadow_only` for both the sender and receiver sessions.

The same automatic workflow SHALL use that `shadow_only` mode for the subsequent direct mailbox operations it drives through those sessions, including `mail send`, `mail check`, `mail reply`, and `stop-session` steps for the same demo root.

#### Scenario: Fresh automatic live run starts both sessions in shadow-only mode
- **WHEN** automatic mailbox roundtrip coverage starts a fresh sender session and receiver session for the tutorial pack
- **THEN** the sender session starts with `parsing_mode=shadow_only`
- **AND THEN** the receiver session starts with `parsing_mode=shadow_only`
- **AND THEN** the automatic workflow records `shadow_only` as the demo parsing mode for that run

#### Scenario: Stepwise automatic workflow reuses persisted shadow-only mode
- **WHEN** automatic mailbox roundtrip coverage has already completed `start` for one demo root with recorded parsing mode `shadow_only`
- **AND WHEN** it later runs `roundtrip` or `stop` for that same demo root without another parsing-mode override
- **THEN** those later steps reuse the persisted `shadow_only` mode
- **AND THEN** the CAO-backed mail and stop operations for that run continue to use `shadow_only`

### Requirement: Automatic mailbox roundtrip coverage does not use `cao_only` or mixed-mode fallback
The automatic mailbox roundtrip workflow SHALL treat `shadow_only` as the only valid CAO parsing mode for satisfying this coverage.

If the automatic workflow is configured with `cao_only`, or if a mailbox step fails under `shadow_only`, the workflow SHALL NOT rerun the same automatic mailbox roundtrip by switching either the Claude sender or the Codex receiver to `cao_only`. The original `shadow_only` result SHALL remain authoritative for that run.

#### Scenario: Explicit `cao_only` request is rejected for automatic live coverage
- **WHEN** automatic mailbox roundtrip coverage is invoked with CAO parsing mode `cao_only`
- **THEN** the workflow fails before reporting a successful mailbox roundtrip
- **AND THEN** the failure explains that automatic mailbox coverage requires `shadow_only`

#### Scenario: Shadow-only failure is surfaced without `cao_only` fallback
- **WHEN** the Claude sender or Codex receiver fails a mailbox step during automatic mailbox coverage under `shadow_only`
- **THEN** the workflow reports that `shadow_only` failure directly
- **AND THEN** it does not retry the same automatic run with either participant switched to `cao_only`
- **AND THEN** it does not report the run as a successful mailbox roundtrip

### Requirement: Automatic mailbox coverage treats Codex shadow parsing as the supported receiver path
For the mailbox roundtrip automatic workflow, the Codex receiver SHALL be treated as a supported `shadow_only` participant rather than as a case that must be downgraded to `cao_only` for automation to proceed.

#### Scenario: Codex receiver remains on the shadow-only path
- **WHEN** automatic mailbox roundtrip coverage starts the Codex receiver for the tutorial pack
- **THEN** the workflow uses the runtime Codex shadow-parser-backed CAO path for that receiver
- **AND THEN** a Codex shadow-only parser or turn failure is surfaced as the mailbox automation result for that run
- **AND THEN** the workflow does not downgrade the receiver to `cao_only` to continue the automatic roundtrip
