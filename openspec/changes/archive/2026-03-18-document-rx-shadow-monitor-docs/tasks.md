## 1. Refresh the developer TUI parsing guide

- [x] 1.1 Update `docs/developer/tui-parsing/architecture.md` and `docs/developer/tui-parsing/index.md` so they describe the current split between `cao_rx_monitor.py` and `cao_rest.py` instead of the removed `_TurnMonitor` implementation.
- [x] 1.2 Update `docs/developer/tui-parsing/shared-contracts.md` so it documents `normalized_text` as the lifecycle-evidence surface and `dialog_text` as the best-effort operator/extraction surface.
- [x] 1.3 Rewrite `docs/developer/tui-parsing/runtime-lifecycle.md` so its diagrams, state/event descriptions, and success/stall rules match the shipped Rx readiness/completion monitor semantics.
- [x] 1.4 Update `docs/developer/tui-parsing/maintenance.md` so it names the current runtime monitor sources, tests, and required doc touchpoints for future shadow-lifecycle changes.
- [x] 1.5 Update `docs/developer/tui-parsing/claude.md` and `docs/developer/tui-parsing/codex.md` so they preserve the parser/runtime boundary without implying that current runtime lifecycle still depends on `TurnMonitor` or `dialog_text`-based lifecycle diffing.

## 2. Refresh operator-facing reference and troubleshooting docs

- [x] 2.1 Update `docs/reference/realm_controller.md` so the `shadow_only` contract, policy list, and diagnostics summary include `completion_stability_seconds` and the shipped completion/stall semantics.
- [x] 2.2 Update `docs/reference/cao_claude_shadow_parsing.md` so its source-file map, sequence diagram, and summary reflect the current runtime monitor boundary and link back to the canonical developer guide.
- [x] 2.3 Update `docs/reference/cao_shadow_parser_troubleshooting.md` so it documents `completion_stability_seconds`, current shadow diagnostics, and the actual completion-timeout explanation operators should use after the Rx monitor rewrite.

## 3. Finalize navigation and source alignment

- [x] 3.1 Decide whether the existing developer-guide pages are sufficient or whether one new focused TUI parsing page is needed; if a new page is needed, create it and link it from the relevant indexes.
- [x] 3.2 Update `docs/index.md`, `docs/reference/index.md`, and `docs/developer/tui-parsing/index.md` as needed so the maintained TUI parsing explanation remains discoverable.
- [x] 3.3 Verify the updated docs against `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/launch_plan.py`, `tests/unit/agents/realm_controller/test_cao_rx_monitor.py`, and `openspec/changes/rx-shadow-turn-monitor/`, then fix any remaining wording drift before implementation is considered done.
