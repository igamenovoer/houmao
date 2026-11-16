# DSH Provider Integration Roadmap

This implementation record tracks the ordered scope of [issue #74](https://github.com/igamenovoer/houmao/issues/74). Its evidence comes from the two OpenSpec changes and their scenario maps. Completion requires both ACP headless and interactive Web acceptance; native conformance, controlled browser checks, and paid-provider results remain separate.

Implementation is complete in [commit 07e74da4](https://github.com/igamenovoer/houmao/commit/07e74da419d04f716454cce343530abf19d32322) on `devel`: headless ACP has 29/29 completed tasks and interactive Web has 35/35. Both changes have synchronized main specifications. The issue follow-up below records closure separately from OpenSpec archive work.

## Postponed Pi Integration

Pi integration ([#75](https://github.com/igamenovoer/houmao/issues/75)) is postponed. It is excluded from the current implementation sequence and has no scheduled start date. The issue remains open for future reprioritization. Work on existing providers, including DSH, can proceed independently.

## Accepted Headless Predecessor

`dsh-01-add-acp-headless-backend` completed all 29 tasks before Web implementation began. Its seven delta specifications were synchronized. The final headless full unit gate passed 4,018 tests with 14 skipped; its final controlled native matrix passed 17 cases. The explicitly selected DeepSeek Messages manager smoke passed tool completion, exact resume, usage, interruption, and two-home isolation. The [headless acceptance map](../../../docs/reference/run-phase/dsh-headless-acceptance.md) records all 61 scenarios and the self-hosted live limitation.

## Interactive Web Implementation

`dsh-02-add-interactive-web-backend` selects native Web for DSH's existing interactive posture and preserves explicit ACP headless selection. Owned local hosts publish a clean origin and exact session identity. Separate authenticated API/browser peers share that session; native conditional handoff controls ordinary delivery. Supervision, terminal-only controls, and browser observation remain separate.

The final combined native suite passed 84 cases (17 predecessor and 67 Web/qualification) in 297.72 seconds. It includes actual browser/API coexistence, both generic raw/manager protocols, native lifecycle/admission, gateway/CCCC/mail, passive observation, cancellation lifetime, accounting, and outer manager exact relaunch. Final unit tests passed 4,150 with 14 skipped in 91.20 seconds; format left 955 files unchanged, Ruff lint passed, and strict mypy passed 470 source files. The [Web acceptance map](../../../docs/reference/run-phase/dsh-web-acceptance.md) covers all 96 delta scenarios with concrete references.

The explicitly selected real DeepSeek Web manager lane passed seven checks: API/browser shell tools, exact continuation, human-origin usage, human-turn interruption, exact host relaunch, and two-home isolation. It used `deepseek-flash`, Messages, unattended posture, native protocol 1, and Chromium 156.0.8078.4. Cleanup succeeded; no credential snapshot or paid transcript was copied into tracked evidence.

All tmux-backed tests clear inherited `TMUX` and `TMUX_PANE` and target explicit private sockets or labels. Cleanup touches only captured owned identities. Credentials, browser tokens/cookies, signed URLs, and live transcripts stay outside the checkout. The opt-in Web runner refuses ambient authentication and reports `not_run` when no external env file is selected.

## Final Audit and Closure Boundary

Functional, code-quality, native, and selected DeepSeek live acceptance have passed. Strict docs/local-link/secret checks and distribution build, Twine metadata, current-byte, and resource-boundary audits also pass. Wheel and sdist each contain 992 files and all 18 required DSH resources. The 61-row and 96-row maps have no missing scenarios, duplicates, or unresolved test references. Accounting tests retain mixed native turns once, separate human follow-ups, actual selected model/provider attribution, and immutable generation/cutoff history across outer manager relaunch. A configured compatible self-hosted deployment/model must be qualified separately when available; absent prerequisites remain `not_run`.

Web main-spec synchronization is complete: 241 current main specs validate normally and change 02 passes strict validation. Historical change 01 passes strict validation against its SHA-verified captured 240-spec baseline; current-main comparison has one expected historical full-block mismatch after the Web scenario was added. Main warning baselines remain unchanged, with no introduced errors or warnings. The [acceptance map](../../../docs/reference/run-phase/dsh-web-acceptance.md#acceptance-state) records that version boundary explicitly.

This combined implementation roadmap scope is complete. Issue #74 was closed on 2026-11-16 with an [implementation and verification note](https://github.com/igamenovoer/houmao/issues/74#issuecomment-6918449890) covering both requested postures. OpenSpec review and archive remain workflow follow-ups.

## Related GitHub Issues

Issue status was reviewed on 2026-11-16. DSH implementation evidence supports the completed closure of #74. Related requests retain their own acceptance criteria.

| Issue | Status | Evidence or Remaining Work |
| --- | --- | --- |
| [#74: DSH backend](https://github.com/igamenovoer/houmao/issues/74) | Closed as completed | Commit `07e74da4`; both ordered changes, 61/96 scenario maps, 4,150 unit tests, 84 native tests, and live DeepSeek ACP/Web qualification. |
| [#60: Codex profile environment](https://github.com/igamenovoer/houmao/issues/60) | Open | The archived [environment regression](../../../tests/integration/srv_ctrl/test_launch_profile_env_to_codex_tui.py) was rerun with an explicit private tmux socket. It stops before provider startup because the synthetic Codex `0.140.0` has no compatible unattended `raw_launch` strategy. Current environment propagation is therefore unverified by that rerun. |
| [#63: Persist gateway execution posture](https://github.com/igamenovoer/houmao/issues/63) | Open | Gateway foreground/background launch overrides exist; persisting that execution-mode preference in reusable profiles remains separate work. |
| [#64: Tool-specific launch options](https://github.com/igamenovoer/houmao/issues/64) | Open | DSH setup/model selection does not complete the requested general tool-option surface or Codex fast-mode controls. |
| [#69: Public integration SDK](https://github.com/igamenovoer/houmao/issues/69) | Open | Internal backend integration does not establish the requested general public SDK. |
| [#75: Pi backend](https://github.com/igamenovoer/houmao/issues/75) | Postponed; issue open | Resume after explicit reprioritization. Retain RPC, persistence, usage, and reload qualification requirements for that future integration. |
| [#81: Execution-owner-aware lifecycle](https://github.com/igamenovoer/houmao/issues/81) | Open | Cross-user, container, and remote-executor ownership and control routing remain outside the owned local DSH host boundary. |
| [#82: Coordinated live refresh](https://github.com/igamenovoer/houmao/issues/82) | Open | DSH resource activation is startup-only and managed HMR remains disabled. Coordinated revision activation and active-turn recovery still require implementation. |
| [#84: Authenticated remote gateways](https://github.com/igamenovoer/houmao/issues/84) | Open | Independent local browser/API peers do not provide the requested remote exposure, TLS/proxy, mailbox authorization, and role boundaries. |
