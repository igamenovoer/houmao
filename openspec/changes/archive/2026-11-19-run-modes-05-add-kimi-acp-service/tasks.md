# Tasks

## 1. Bind Kimi to the Shared Service Owner

- [x] 1.1 Register `(kimi, service)` with `kimi_acp` and mode-specific policy under the 04 owner. Verify the manager starts the selected `kimi acp` executable, private home, workspace and auth projection before reporting readiness.
- [x] 1.2 Implement Kimi initialization and qualified session new/resume/load handling. Verify the exact private home and workspace before resume, and isolate loaded history from new request output and usage. Test missing capabilities and foreign or missing native sessions.
- [x] 1.3 Document the supported Kimi service build, negotiated operations, and distinction between history replay and current output. Compare the operator example and capability output with a native handshake.

## 2. Implement Turn and Interaction Semantics

- [x] 2.1 Wire `session/prompt`, session updates, permissions and supported interactions into the owner. Exercise a reverse request while a prompt is pending under the selected policy and verify unsupported requests finish within the declared bound.
- [x] 2.2 Persist transport handoff after prewrite authorization. Fence cancellation and settlement with managed request, incarnation, correlated reply and exact native journal. Test two turns on one native process, late updates, stale interrupts and disconnect without input replay.
- [x] 2.3 Verify signed gateway request state and usage, passive state and usage, and AG-UI output joined to the same request ID. Document context-only ACP usage, replay and unsupported client facilities.

## 3. Qualify Kimi Service End to End

- [x] 3.1 Run the fixture helper with Kimi `2.6.0` and self-hosted `Qwen/Qwen3.8-27B-FP8`. Exercise manager and authenticated gateway prompts, ordinary mail or plugin delivery while busy, gateway reattach, stop, and exact continuation after relaunch.
- [x] 3.2 Run affected Pixi unit and integration suites on an isolated tmux server. Record the qualified build and compare results for Kimi's existing headless and TUI launches before enabling the new pair.
