## 1. Runtime Launch and Control

Dependency note: Kimi shared TUI tracking and parser-facing replay must consume the recorded signal corpus and contracts from `capture-kimi-tui-signals`. Do not extend these tasks by inventing new Kimi TUI heuristics outside that corpus/contract workflow.

- [ ] 1.1 Add `kimi` to `local_interactive` tool admission, backend selection, role-injection planning, and managed launch validation paths without changing `kimi_headless`.
- [ ] 1.2 Add Kimi TUI process recognition for `kimi-code` and `kimi` in local runtime, server fallback tracking, passive observation, and control CLI allowlists.
- [ ] 1.3 Extend Kimi model-selection projection so local interactive Kimi launches and resumed Kimi TUI relaunches receive final `--model <alias>` arguments when launch-owned model selection is resolved.
- [ ] 1.4 Implement Kimi local interactive relaunch arguments for fresh, `--continue`, and `--session <session_id>` modes, with no bare `--session` picker path.
- [ ] 1.5 Reject Kimi TUI relaunch before provider start when resumed startup would combine `--continue` or `--session <session_id>` with `--yolo`, `--auto`, or `--plan`.
- [ ] 1.6 Confirm Kimi TUI prompt submission works through the existing semantic paste-plus-submit path and keep raw control-input handling separate.
- [ ] 1.7 Confirm Kimi TUI interrupt uses Escape for active streams and modal surfaces, with no double-Ctrl+C primary path.
- [ ] 1.8 Set `KIMI_CODE_NO_AUTO_UPDATE=1` for managed Kimi TUI launches and cover the launch environment projection in tests.
- [ ] 1.9 Keep managed `--skills-dir` projection scoped to Kimi headless prompt mode; do not add prompt-mode-only skills-dir args to Kimi TUI launch.

## 2. Parser and Shared TUI Tracking

- [ ] 2.1 Add a Kimi visible-surface parser that returns supported `HoumaoParsedSurface` values for ready, active, approval-blocked, startup-modal, and unknown Kimi surfaces by wrapping Kimi-specific analysis directly.
- [ ] 2.2 Wire the Kimi parser into the official parser adapter without routing Kimi through the Claude/Codex shadow parser stack.
- [ ] 2.3 Consume the `capture-kimi-tui-signals` `kimi_code` shared tracker app id/profile registration instead of adding a separate profile path.
- [ ] 2.4 Extend the recorded-contract-backed Kimi detector only when new Kimi versions are covered by labeled corpus evidence.
- [ ] 2.5 Reuse the recorded-contract-backed ready, draft, activity, approval, success, interruption, and footer metadata signals for official parser/tracker integration.
- [ ] 2.6 Keep footer model metadata such as `thinking` governed by the `capture-kimi-tui-signals` contract: footer metadata alone does not emit active-turn evidence.
- [ ] 2.7 Ensure server, gateway, and passive observer diagnostics report Kimi as supported when process inspection and parser support are available.

## 3. Tests and Fixtures

- [ ] 3.1 Add Kimi TUI text fixtures for idle welcome/editor, active response, completed response, command approval, rejected command, and footer-thinking-with-ready-prompt surfaces.
- [ ] 3.2 Add unit tests for Kimi parser state mapping and approval dialog excerpts.
- [ ] 3.3 Add unit tests for Kimi shared tracker profile resolution and normalized signal detection.
- [ ] 3.4 Add launch-plan and relaunch tests covering Kimi local interactive backend selection, `--model`, `--continue`, `--session <session_id>`, no bare `--session`, and rejection of resumed `--yolo`/`--auto`/`--plan` combinations.
- [ ] 3.5 Add process-inspection and allowlist tests proving `kimi-code` and `kimi` are recognized as Kimi TUI process names.
- [ ] 3.6 Add tests proving managed Kimi TUI launch projects `KIMI_CODE_NO_AUTO_UPDATE=1` and does not project managed `--skills-dir`.
- [ ] 3.7 Add or update manual/live probe notes for installed Kimi Code behavior when logged-in credentials are available.

## 4. Documentation and Validation

- [ ] 4.1 Update run-phase backend and relaunch documentation to include Kimi Code local interactive support, provider-native continuation arguments, resumed-startup conflicts, model selection, update suppression, and headless-only `--skills-dir` projection.
- [ ] 4.2 Keep Kimi headless docs and launch-policy registry behavior distinct from Kimi TUI support.
- [ ] 4.3 Run `openspec status --change add-kimi-tui-support` and fix any artifact or schema issues.
- [ ] 4.4 Run focused unit tests for launch planning, parser/tracking, and process inspection.
- [ ] 4.5 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test` before archiving the change.
