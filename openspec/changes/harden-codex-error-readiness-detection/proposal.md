## Why

Recent upstream Codex behavior shows failed turns through more than one visual surface: prompt-adjacent red error cells, warning-only failure rows, and transient retry or reconnect status. Houmao's current Codex tracker is too tightly coupled to narrow literal error text, which lets some failed or retrying surfaces look like successful ready returns even though input readiness itself is still valid.

## What Changes

- Harden Codex tracked-TUI failure detection around bounded signal families instead of exact full-string matches.
- Distinguish prompt-ready terminal failure surfaces from live retry or reconnect surfaces so the tracker can preserve truthful input readiness without settling success incorrectly.
- Continue treating prompt-adjacent compact or server failures as recoverable degraded context when their bounded failure text matches the essential compact or server semantics, without forcing a context reset.
- Recognize prompt-adjacent warning-only terminal failures that return to a visible prompt as failure blockers rather than ready-success candidates.
- Recognize transient retry or reconnect status surfaces near the live edge as active evidence rather than prompt-ready success candidates.
- Keep historical transcript warnings and old failure text outside the bounded current-turn scope from mutating the current readiness, failure, or degraded-context decision.
- Add regression coverage using updated upstream Codex error and warning examples so future detector updates are anchored to observed signal families.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `codex-tui-state-tracking`: broaden Codex current-turn failure detection from narrow red-cell literal matching to bounded structural and semantic signal families, while preserving prompt-ready posture when the composer is genuinely ready.
- `official-tui-state-tracking`: define how prompt-ready terminal failures, degraded compact failures, and transient retry surfaces affect public readiness, active, and completion semantics.
- `versioned-tui-signal-profiles`: require drift-prone Codex status and error matching to rely on bounded structural patterns and essential semantic tokens rather than exact full-sentence literals.

## Impact

- Affected code includes Codex tracked-TUI detectors and helper modules under `src/houmao/shared_tui_tracking/apps/codex_tui/`, shared tracker state reduction under `src/houmao/shared_tui_tracking/session.py`, and Codex tracker regression coverage under `tests/unit/shared_tui_tracking/` and `tests/unit/server/`.
- The public tracked-state contract remains centered on `surface.*`, `turn.phase`, `last_turn.*`, and `chat_context`, but some Codex surfaces that currently drift into `success` or generic ready state will instead remain active, block success, or publish recognized failure state.
- No external dependency, storage migration, or protocol version bump is required.
