# Tasks

## 1. Replace the Retired Wire Contract

- [x] 1.1 Register fresh `(codex, service)` launches with the owner from 04 and retain a current-schema check for persisted authority. Test qualified fresh launch, incompatible legacy manifests, and version failures that name available modes.
- [x] 1.2 Replace the retired client with private stdio `initialize`, `initialized`, and exact `thread/start` or `thread/resume`. Check the negotiated home, persisted thread workspace and exact response, and prove the service cannot adopt an unrelated listener or silently create a replacement thread.
- [x] 1.3 Document executable selection, native home, protocol qualification, and owner-bound lifecycle. Exercise the public project launch example and match the reported mode, backend, service incarnation, and selected thread.

## 2. Correlate Turns and Native Requests

- [x] 2.1 Recheck admission under the prewrite guard and encode `turn/start` with `threadId` and typed `input` items. Test a response before and after matching notifications. Keep the native handle separate from terminal settlement.
- [x] 2.2 Stream item and terminal events, process server-initiated approval/input requests, and handle bounded unsupported requests while draining the connection. Test normal, failed, partial and uncertain outcomes plus foreign and duplicate notifications.
- [x] 2.3 Implement `turn/interrupt` for the verified active thread and turn and keep client detach independent of provider stop. Test stale interrupts, continued service after gateway reconnect, and owner cleanup on explicit stop.
- [x] 2.4 Document what a turn handle, terminal notification, and uncertain connection establish. Verify manager, gateway, and AG-UI results preserve those distinctions in their public projections.

## 3. Qualify the Native App-Server

- [x] 3.1 Use Codex CLI `0.169.0` and the self-hosted `Qwen/Qwen3.8-27B-FP8` Responses fixture. Perform two prompts on one service, a scoped interrupt, gateway replacement, and explicit relaunch with exact thread continuation. Record build and native evidence outside the checkout.
- [x] 3.2 Run the app-server, runtime, registry, and gateway Pixi suites with isolated tmux. Re-run existing Codex headless and TUI qualification cases and verify the service support matrix matches the native result.
