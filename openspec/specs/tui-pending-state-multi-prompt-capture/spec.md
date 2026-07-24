# TUI Pending State Multi Prompt Capture Specification

## Purpose
TBD - created by archiving change expand-tui-pending-capture-multi-prompt. Update Purpose after archive.

## Requirements

### Requirement: Capture sessions with one, two, and three coexisting pending prompts
The runner SHALL support per-provider lifecycle manifests that target exactly 1, 2, or 3 pending prompts coexisting with an active turn.

#### Scenario: 1-pending session completes
- **WHEN** the runner executes the `claude-1-pending.json` lifecycle
- **THEN** the recording contains a span labeled `has_pending_message=yes` and `pending_count=1`

#### Scenario: 2-pending session completes
- **WHEN** the runner executes the `codex-2-pending.json` lifecycle
- **THEN** the recording contains a span labeled `has_pending_message=yes` and `pending_count=2`

#### Scenario: 3-pending session completes
- **WHEN** the runner executes the `kimi-3-pending-long.json` lifecycle
- **THEN** the recording contains a span labeled `has_pending_message=yes` and `pending_count=3`

### Requirement: Include one long prompt of approximately 500 characters
The 3-pending-long lifecycle SHALL submit one prompt whose raw text is at least 480 and at most 520 characters, including a unique canary substring.

#### Scenario: Long prompt is identifiable in snapshots
- **WHEN** the analyzer reviews the 3-pending-long recording
- **THEN** the long prompt's canary substring appears in at least one pending-span snapshot

### Requirement: Label template exposes pending count
Each sample label SHALL include `pending_count` in addition to `can_accept_input` and `has_pending_message`.

#### Scenario: Count matches binary flag
- **WHEN** a sample is labeled `has_pending_message=no`
- **THEN** its `pending_count` SHALL be `0`

#### Scenario: Count reflects visible queue depth
- **WHEN** a sample is labeled `has_pending_message=yes`
- **THEN** its `pending_count` SHALL be `1`, `2`, `3`, or `unknown`, derived from visible provider signatures

### Requirement: Analyzer estimates count from provider-specific patterns
Each lifecycle manifest SHALL declare `pending_count_patterns` that the analyzer uses to estimate queue depth.

#### Scenario: Count extracted by marker counting
- **WHEN** a manifest declares `pending_count_patterns.extractor` as `count_markers` with a `marker_regex`
- **THEN** the analyzer SHALL set `pending_count` to the number of non-overlapping marker matches in the visible pane text

#### Scenario: Unknown count on conflict
- **WHEN** the analyzer detects pending signature but cannot reliably count markers
- **THEN** the analyzer SHALL label `pending_count` as `unknown` and record the conflict in `evidence_note`

### Requirement: Review video displays pending count
The review video SHALL render `pending_count` in the right-side info panel for every frame.

#### Scenario: Video panel shows count
- **WHEN** a frame corresponds to a sample with `pending_count=2`
- **THEN** the right panel SHALL display `pending_count: 2`

### Requirement: Cap-partial attempts are preserved and tainted
If a provider visibly queues fewer prompts than the target count, the runner SHALL still freeze the recording and labels and mark the attempt tainted.

#### Scenario: Provider caps at two pending prompts
- **WHEN** the 3-pending-long lifecycle reaches only two pending prompts
- **THEN** the run is marked `pending_count_capped_at_2` and the recording is frozen with labels for the reached count

### Requirement: No modifications under src/houmao
All implementation code for this capability SHALL live under `scripts/qualification/tui-prompt-admission/`.

#### Scenario: Source tree audit
- **WHEN** the change is submitted
- **THEN** no new or modified files SHALL appear under `src/houmao/`
