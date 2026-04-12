## 1. Shared Timing Model And Persistence

- [x] 1.1 Add a shared gateway TUI tracking timing model with positive-float validation for poll interval, stability threshold, completion stability, unknown-to-stalled timeout, and stale-active recovery.
- [x] 1.2 Extend `SingleSessionTrackingRuntime` to accept and forward stale-active recovery seconds into `LiveSessionTracker` while preserving existing defaults.
- [x] 1.3 Extend gateway desired configuration to store optional gateway TUI tracking timing configuration and read old desired-config files that omit it.
- [x] 1.4 Add helpers that resolve effective gateway TUI tracking timing values from explicit overrides, persisted desired config, and defaults.

## 2. Gateway Attach And Service Plumbing

- [x] 2.1 Extend `RuntimeSessionController.attach_gateway()` and `_attach_gateway_for_controller()` to accept optional gateway TUI timing overrides.
- [x] 2.2 Pass resolved timing values into both same-session auxiliary-window and detached-process gateway service launch commands.
- [x] 2.3 Extend the internal gateway service CLI to accept `--tui-*` timing arguments and pass them into `GatewayServiceRuntime`.
- [x] 2.4 Start gateway-owned TUI tracking with the resolved timing configuration in `GatewayServiceRuntime`.
- [x] 2.5 Persist the resolved timing configuration after successful gateway attach alongside desired host, port, and execution mode.

## 3. Public CLI And API Surfaces

- [x] 3.1 Add `--gateway-tui-*` timing options to `houmao-mgr agents gateway attach` and forward them through local and pair-managed attach paths.
- [x] 3.2 Extend `HoumaoManagedAgentGatewayAttachRequest` and server attach handling to accept, validate, and forward gateway TUI timing configuration.
- [x] 3.3 Add `--gateway-tui-*` timing options to `houmao-mgr project easy instance launch` and pass them into launch-time gateway auto-attach.
- [x] 3.4 Reject `project easy instance launch --no-gateway` when any gateway TUI timing override is supplied.
- [x] 3.5 Keep launch-profile and easy-profile stored defaults unchanged when timing overrides are supplied as one-shot launch options.

## 4. Tests And Documentation

- [x] 4.1 Add unit tests for desired-config persistence, default fallback, and invalid timing validation.
- [x] 4.2 Add unit tests for local gateway attach command plumbing, server attach request forwarding, and internal gateway service CLI argument parsing.
- [x] 4.3 Add unit tests for `project easy instance launch` timing option forwarding and `--no-gateway` conflict handling.
- [x] 4.4 Update CLI reference, gateway lifecycle documentation, and relevant system-skill guidance to document the new `--gateway-tui-*` options.
- [x] 4.5 Run focused gateway/easy-launch tests plus `openspec validate --changes expose-gateway-tui-tracking-timings`.
