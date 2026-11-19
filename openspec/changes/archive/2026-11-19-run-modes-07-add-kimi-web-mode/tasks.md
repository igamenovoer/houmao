# Tasks

## 1. Qualify Native Web and Managed Readiness

- [x] 1.1 Inspect installed Kimi Code `2.6.0` and verify through real Chromium and self-hosted `Qwen/Qwen3.8-27B-FP8` that a concurrent browser turn can cause stock submission to queue. Record exact native evidence.
- [x] 1.2 Use the shared owner reservation, verify live native readiness immediately before each ordinary POST, and preserve the native receipt if the browser wins after the check. Test observed busy, native queueing, revocation and no replay.
- [x] 1.3 Document accepted readiness semantics and supported builds. Verify an incompatible selection fails before preparing or replacing an existing owner.

## 2. Bind Browser and Machine Clients to One Host

- [x] 2.1 Register `kimi_web`, private native home, loopback host supervision, and exact session binding. Verify wrong listener and stale owner handling without sending credentials.
- [x] 2.2 Protect native startup output and publish an exact, token-free browser handoff. Verify explicit private browser access and that public state and logs contain no bearer or token fragment.
- [x] 2.3 Project exact request, native prompt ID, queue state, and terminal evidence through gateway, passive, and AG-UI. A browser turn cannot settle unrelated managed work. Reading a cold session cannot activate it.
- [x] 2.4 Implement exact abort, gateway reattachment, owner stop, and native-session relaunch. Verify stale prompt refusal and ambiguous response handling.

## 3. Verify Mixed Control

- [x] 3.1 Run Chromium on the real managed Kimi host. Verify the gateway refuses input while the browser is observed busy, and document the accepted post-check race.
- [x] 3.2 Exercise successful browser and gateway turns in the same conversation through public manager, gateway and passive APIs using the selected Qwen model. Record attributable native identity and actual accounting.
- [x] 3.3 Run affected Pixi suites in isolated tmux and record the exact live build, fixture, tests, and gaps under `logs/`.
