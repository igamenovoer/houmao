## Why

Codex prompt editing detection is currently coupled to detector-local placeholder heuristics, which makes the tracker brittle when upstream Codex changes how the prompt area is rendered. We need a version-aware behavior boundary that can absorb prompt-render drift without rewriting shared tracker logic or hard-coding one detection technique as the permanent design.

## What Changes

- Replace the current Codex prompt placeholder heuristic with a version-selected prompt behavior variant that classifies prompt-area snapshots into conservative prompt kinds such as `placeholder`, `draft`, `empty`, or `unknown`.
- Resolve Codex prompt behavior through the shared versioned profile contract so future Codex version families can swap in new prompt-classification logic without changing shared tracker state reduction.
- Require Codex prompt-classification variants to degrade to `unknown` when they cannot confidently distinguish placeholder presentation from real user draft input, and expose variant/debug notes for drift investigation.
- Add fixture-backed coverage for representative Codex prompt-area states, including idle placeholder, real typed draft, disabled-input prompt, dynamic placeholder flows, and unrecognized prompt presentation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: extend the shared versioned profile contract so Codex prompt-area interpretation can vary by selected profile or profile-owned behavior variant.
- `codex-tui-state-tracking`: change Codex editing-input semantics to derive from a version-selected prompt behavior classification instead of a detector-local placeholder string list.

## Impact

- Affected code:
  - `src/houmao/shared_tui_tracking/apps/codex_tui/`
  - `src/houmao/shared_tui_tracking/registry.py`
  - shared surface/prompt parsing helpers as needed
- Tests:
  - `tests/unit/shared_tui_tracking/`
  - fixture-backed replay/live-watch coverage for Codex prompt-area drift cases
- Operational impact:
  - live-watch/debug output may expose more specific Codex detector or prompt-variant notes when prompt rendering is unrecognized
