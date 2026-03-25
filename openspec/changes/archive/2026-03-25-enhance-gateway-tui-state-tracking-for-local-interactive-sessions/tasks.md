## 1. Gateway tracking identity admission

- [x] 1.1 Extend `GatewayServiceRuntime._tui_tracking_identity_locked()` so attached runtime-owned `local_interactive` sessions build a `HoumaoTrackedSessionIdentity` instead of returning `None`.
- [x] 1.2 Derive the local-interactive tracked identity from runtime-owned attach-contract fields, use the runtime session id as the canonical tracked-session identity, and keep manifest-derived enrichment best-effort.

## 2. Gateway-owned TUI tracking behavior

- [x] 2.1 Ensure gateway startup activates `SingleSessionTrackingRuntime` for attached runtime-owned `local_interactive` sessions through the existing tracking startup path.
- [x] 2.2 Ensure gateway-local TUI state, TUI history, and explicit prompt-note tracking succeed for attached `local_interactive` sessions without introducing a separate local-interactive-only route surface.

## 3. Automated validation

- [x] 3.1 Add gateway-focused automated coverage for attached runtime-owned `local_interactive` tracking startup and gateway-local TUI route availability.
- [x] 3.2 Add automated coverage that prompt submission through the gateway records explicit prompt-submission evidence for tracked `local_interactive` sessions.
- [x] 3.3 Run the relevant gateway support tests and confirm the change works without requiring `houmao-server`.
