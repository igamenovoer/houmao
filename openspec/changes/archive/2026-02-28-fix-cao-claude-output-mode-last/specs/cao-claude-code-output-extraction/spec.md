## ADDED Requirements

### Requirement: Claude Code CAO output is parsed by a runtime shadow provider
When using CAO provider `claude_code`, the system SHALL treat CAO as a transport layer and derive both:
1) Claude Code turn status (shadow status), and
2) the last assistant message (answer text),
from `GET /terminals/{terminal_id}/output?mode=full`.

The system SHALL NOT rely on:
- CAO `GET /terminals/{terminal_id}` `status` for turn gating, or
- CAO `mode=last` output for answer extraction,
because those behaviors are derived from upstream regexes that are known to drift.

#### Scenario: CAO reports `idle` but runtime shadow status remains `processing`
- **WHEN** CAO terminal `status` is `idle`
- **AND WHEN** recent `mode=full` output contains a spinner-only line like `✽ Razzmatazzing…` for the current turn
- **THEN** the system classifies the terminal as `processing` via shadow status and does not treat the turn as complete

### Requirement: Claude Code parsing preset is resolved by version
The system SHALL resolve a single Claude Code parsing preset that controls:
1) assistant response marker detection,
2) spinner/processing detection,
3) idle prompt detection (used for shadow status and extraction stop conditions), and
4) separator line detection (for example `────────`).

Preset selection SHALL follow this priority order:
1) `AGENTSYS_CAO_CLAUDE_CODE_VERSION` environment variable (when set and non-empty),
2) auto-detected Claude Code version from the scrollback banner (for example `Claude Code v2.1.62`), and
3) latest known preset (fallback).

If version detection fails entirely (no banner/version found), the system SHALL use the latest known preset. Operators MAY set `AGENTSYS_CAO_CLAUDE_CODE_VERSION` to pin a specific preset when the latest patterns do not match.

When selecting a preset for a requested/detected version `V`, the system SHALL:
- use an exact-match preset when present, otherwise
- use the closest previous preset (floor lookup), and
- if `V` is older than the oldest known preset, use the oldest (baseline) preset.

#### Scenario: Env override pins the parsing preset
- **GIVEN** `AGENTSYS_CAO_CLAUDE_CODE_VERSION=2.1.62` is set for the runtime process
- **WHEN** the system evaluates Claude Code output for shadow status or extraction
- **THEN** it uses the 2.1.62 parsing preset regardless of what the scrollback banner reports

### Requirement: Shadow status classification is output-driven and bounded
The system SHALL compute shadow status for Claude Code from a bounded tail window of the `mode=full` output, and SHALL default to the last 100 lines from the end of the output.

The system SHALL classify at least:
- `processing` when a preset-recognized spinner line ending with `…` is present,
- `waiting_user_answer` when selection UI is present, and
- `completed` when an idle prompt is present and a preset-recognized response marker appears after the current-turn baseline, and
- `idle` when an idle prompt is present and no higher-priority state matches.

#### Scenario: Status checks avoid stale scrollback false positives
- **WHEN** the tmux scrollback contains an old spinner line from a previous turn
- **AND WHEN** the bounded tail window for the current status check does not include that spinner line
- **THEN** the system does not classify the terminal as `processing` based on stale output

#### Scenario: Completed shadow state requires a post-baseline response marker
- **WHEN** the tmux scrollback contains an idle prompt
- **AND WHEN** the tmux scrollback contains a preset-recognized response marker that appears after the current-turn baseline
- **THEN** the system classifies the terminal as `completed`

### Requirement: Answer extraction from `mode=full` is preset-scoped, ANSI-stripped, and prompt-bounded
When extracting the last assistant message for Claude Code from `mode=full` output, the system SHALL:
1) locate the last assistant response marker match from the resolved parsing preset (for example `●` in newer versions, `⏺` in older versions),
2) ensure the match is associated with the current turn by applying a baseline cursor captured at prompt submission time, and
3) extract assistant message text until the next extraction stop boundary, returning plain text with ANSI escape codes removed.

Baseline cursor representation:
- Before prompt submission, capture `baseline_pos` as the character offset of the end of the last response marker match in the current `mode=full` output (or `0` if no match exists).
- If later `mode=full` output is shorter than `baseline_pos` (scrollback reset/truncation), the system SHALL treat the baseline as invalidated and use a safe fallback to avoid extracting an earlier-turn response.

Assistant response marker matching SHALL treat markers as a line-start prefix (after optional ANSI), and SHALL require following whitespace.

Extraction stop boundaries SHALL include:
- an idle prompt line defined by the resolved parsing preset, detected by matching against the ANSI-stripped form of the line (to handle ANSI-prefixed prompts), and
- a separator line containing `────────`.

#### Scenario: Extraction stops at an ANSI-prefixed `❯` prompt
- **WHEN** tmux scrollback contains a Claude Code response followed by an `❯` idle prompt line that is ANSI-prefixed and additional UI chrome
- **THEN** the extracted answer excludes the prompt line and any subsequent UI chrome

### Requirement: Waiting-user-answer is surfaced as an explicit error
If the system detects `waiting_user_answer` for Claude Code during a turn, it SHALL fail the turn with an explicit error and include an ANSI-stripped excerpt showing the selection options.

### Requirement: Runtime does not return raw tmux scrollback as the answer
For Claude Code, the system SHALL not return raw `mode=full` tmux output as the user-facing answer text.

If extraction fails, the system SHALL surface a clear extraction failure instead of returning a styled transcript.
