## 1. Source-Backed Detector Signals

- [x] 1.1 Add bounded Kimi queue-pane extraction for all three maintained queue hints and expose queue activity in the Kimi surface analysis.
- [x] 1.2 Make current Kimi queue panes block ready posture and success while preserving idle-footer and historical-spinner behavior.
- [x] 1.3 Add Kimi unit regressions for moon activity, each queue mode, a spinner displaced by the queue pane, and settled ready return.
- [x] 1.4 Add all maintained Codex pending-input section headers to current-turn activity and non-response classification.
- [x] 1.5 Restrict Codex reconnect activity to bounded source-backed status shapes and remove prose/slash-command retry false positives.
- [x] 1.6 Recognize current Codex list selectors, including the model selector, as bounded blocking overlays.
- [x] 1.7 Add Codex unit regressions from the ST04/ST05 surfaces for pending steers, hidden status, retry prose, reconnect status, and model selector.

## 2. Runtime and Capture Lifecycle

- [x] 2.1 Inspect the live observation interfaces and implement generation-scoped fresh-surface readiness after provider restart.
- [x] 2.2 Add shared runtime replay coverage proving stale pre-restart surfaces remain non-ready until a fresh provider prompt renders.
- [x] 2.3 Make long-horizon provider activity predicates recognize Kimi spinners/queues and Codex pending-input surfaces.
- [x] 2.4 Require a post-submit busy or progress edge before an operation's ready-return gate can succeed, while preserving startup and non-submit ready gates.
- [x] 2.5 Add capture-gate unit coverage for the Kimi premature-ready race and short-stimulus timeout behavior.

## 3. Replay Evidence and Comparator

- [x] 3.1 Split direct UC-03 labels from legacy generated public-state references in the qualification comparator and report terminology.
- [x] 3.2 Make tracker-to-UC03 mapping diagnostics-first and require explicit overlay evidence instead of manufacturing overlays from unknown posture.
- [x] 3.3 Add comparator tests for TUI-down, ambiguous unknown, explicit overlay, busy active, draft, and ready samples.
- [x] 3.4 Add a reproducible recording-replay summary command that reports sustained mismatch intervals separately from short transition-boundary noise.

## 4. Recorded Qualification and Verification

- [x] 4.1 Replay Kimi ST03/ST04 and Codex ST01/ST03/ST04/ST05 at canonical cadence and record before/after mismatch totals.
- [x] 4.2 Replay retained samples at 10 Hz, 5 Hz, and 2 Hz and verify that source-backed busy-before-ready ordering remains intact.
- [x] 4.3 Inspect and document every remaining sustained mismatch class; fix product defects and identify only genuine boundary or legacy-label noise as residual.
- [x] 4.4 Run focused unit tests, the shared TUI tracking unit suite, lint for edited Python files, and OpenSpec validation.
- [x] 4.5 Write the corrected replay test report with artifact paths, residual counts, and a scoped qualification recommendation.
