# Tasks

## 1. Bind Kimi to the Shared Service Owner

- [ ] 1.1 Register `(kimi, service)` with `kimi_acp` and mode-specific policy under the 04 owner. Verify the manager starts the selected `kimi acp` executable, private home, workspace and auth projection before reporting readiness.
- [ ] 1.2 Implement Kimi initialization, client capabilities, and qualified session new/resume/load handling. Test missing capabilities, foreign or missing exact sessions, and replayed history that cannot complete a request or increment current usage.
- [ ] 1.3 Document the supported Kimi service build, negotiated operations, and distinction between history replay and current output. Compare the operator example and capability output with a native handshake.

## 2. Implement Turn and Interaction Semantics

- [ ] 2.1 Wire `session/prompt`, session updates, permissions and supported interactions into the owner. Exercise a reverse request while a prompt is pending under the selected policy and verify unsupported requests finish within the declared bound.
- [ ] 2.2 Fence session-scoped cancellation, settlement, and late updates with managed request, session and incarnation. Test two turns on one native process, a stale interrupt, and disconnect after admission without input replay.
- [ ] 2.3 Expose status and native evidence to gateway, passive and AG-UI consumers. Exercise the public state and event APIs and document observed limitations for replay, usage, and unsupported client facilities.

## 3. Qualify Kimi Service End to End

- [ ] 3.1 Run the fixture helper with an explicitly selected Kimi build, case, and model against the real service. Exercise manager and authenticated gateway prompts, ordinary mail or plugin delivery while busy, gateway reattach, stop, and exact continuation after relaunch.
- [ ] 3.2 Run affected Pixi unit and integration suites on an isolated tmux server. Record the qualified build and compare results for Kimi's existing headless and TUI launches before enabling the new pair.
