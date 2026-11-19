# Tasks

## 1. Replace the Retired Wire Contract

- [ ] 1.1 Register fresh `(codex, service)` launches with the owner from 04 and retain a current-schema check for persisted authority. Test qualified fresh launch, incompatible legacy manifests, and version failures that name available modes.
- [ ] 1.2 Replace the old client handshake and thread logic with stdio `initialize`, `initialized`, and exact `thread/start` or `thread/resume`. Compare requests with the local native protocol and prove the service cannot adopt an unrelated listener or silently create a replacement thread.
- [ ] 1.3 Document executable selection, native home, protocol qualification, and owner-bound lifecycle. Exercise the public project launch example and match the reported mode, backend, service incarnation, and selected thread.

## 2. Correlate Turns and Native Requests

- [ ] 2.1 Encode `turn/start` with `threadId` and typed `input` items. Update the protocol fixtures and test both a prompt response preceding notifications and notifications racing the response.
- [ ] 2.2 Stream item and terminal events, process server-initiated approval/input requests, and handle bounded unsupported requests while draining the connection. Test normal, failed, partial and uncertain outcomes plus foreign and duplicate notifications.
- [ ] 2.3 Implement `turn/interrupt` for the verified active thread and turn and keep client detach independent of provider stop. Test stale interrupts, continued service after gateway reconnect, and owner cleanup on explicit stop.
- [ ] 2.4 Document what a turn handle, terminal notification, and uncertain connection establish. Verify manager, gateway, and AG-UI results preserve those distinctions in their public projections.

## 3. Qualify the Native App-Server

- [ ] 3.1 Use a real selected Codex build and fixture case/model to perform two prompts on one service, a scoped interrupt, gateway replacement, and explicit relaunch with exact thread continuation. Record build and native evidence outside the checkout.
- [ ] 3.2 Run the app-server, runtime, registry, and gateway Pixi suites with isolated tmux. Re-run existing Codex headless and TUI qualification cases and verify the service support matrix matches the native result.
