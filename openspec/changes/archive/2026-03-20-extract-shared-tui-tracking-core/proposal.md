## Why

The repo intentionally keeps a demo/reference tracker independent from the official runtime implementation, but the official/runtime path itself is still fragmented: the live server tracker, terminal-record replay, and the Claude explore harness do not share one authoritative tracking core. That split has already produced a real circular-import failure because generic replay code imports the demo tracker, and it continues to create drift risk across the official/runtime path.

## What Changes

- Introduce a repo-owned shared TUI tracking core for the official/runtime path that owns neutral tracked-state models, lifecycle reduction, and turn-result mapping for parsed observations plus optional input/runtime evidence.
- Move official/runtime turn-signal detector ownership below `houmao.server` and `houmao.explore` so live tracking, recorder replay, and harness replay do not depend upward into adapter-owned detector code.
- Rework the official live tracker to consume that shared core rather than owning the only full implementation of the public `surface` / `turn` / `last_turn` semantics.
- Rework terminal-record replay so it no longer imports demo-owned tracking code and so replay output aligns with the official simplified tracked-state vocabulary.
- Extend `terminal_record add-label` so the existing operator-facing labeling surface can express the official tracked-state vocabulary directly.
- Rework the Claude state-tracking explore harness so its replay path uses the shared core rather than maintaining a separate mirrored reducer.
- Preserve the demo/reference tracker as an intentionally independent implementation rather than making it consume the shared official/runtime core.
- **BREAKING** shift recorder replay and related labels/tests away from demo-era `readiness_state` / `completion_state` as the primary replay contract in favor of the official tracked-state vocabulary and any explicitly retained debug-only reducer fields.

## Capabilities

### New Capabilities
- `shared-tui-tracking-core`: reusable tracked-state models and reduction logic for the official/runtime path that can be consumed by live server tracking, offline recorder replay, and replay/validation harnesses without depending on demo packages or server route adapters.

### Modified Capabilities
- `official-tui-state-tracking`: live tracking must derive its public tracked-state semantics through the shared core while preserving the current server-owned diagnostics and authoritative in-memory state behavior.
- `terminal-record-replay`: replay analysis must align to the official tracked-state vocabulary and stop depending on demo-owned tracking reducers.
- `claude-code-state-tracking-explore-harness`: replay and comparison flows must consume the shared core rather than mirroring the simplified state model in a separate reducer implementation.

## Impact

- Affected code: `src/houmao/server/tui/tracking.py`, `src/houmao/server/tui/turn_signals.py`, `src/houmao/server/models.py`, `src/houmao/terminal_record/service.py`, `src/houmao/explore/claude_code_state_tracking/*`
- Affected tests: `tests/unit/server/test_tui_parser_and_tracking.py`, `tests/unit/terminal_record/test_service.py`, `tests/unit/explore/test_claude_code_state_tracking.py`, and related monitor/demo tests
- Affected artifacts/docs: recorder replay labels and analysis outputs, issue reference `context/issues/known/issue-tracking-semantics-duplicated-across-server-replay-and-demo.md`
