## 1. Easy Launch Gateway Defaults

- [x] 1.1 Add `--no-gateway` and `--gateway-port` to `houmao-mgr project easy instance launch` and reject invalid flag combinations before launch.
- [x] 1.2 Thread easy-launch gateway intent from `project easy instance launch` through the delegated local launch helper into `start_runtime_session(...)`.
- [x] 1.3 Make the default easy attached path request explicit loopback auto-attach with a system-assigned port, while honoring per-launch `--gateway-port` overrides and `--no-gateway` opt-out.

## 2. Launch Result Semantics

- [x] 2.1 Extend easy launch completion output to report resolved gateway host/port when launch-time gateway attach succeeds.
- [x] 2.2 Surface gateway auto-attach errors in the easy launch result without hiding the running session identity or manifest path.
- [x] 2.3 Make degraded-success easy launches return the intended non-zero exit semantics when the session starts successfully but gateway auto-attach fails.

## 3. Verification And Docs

- [x] 3.1 Add automated coverage for default gateway attach, `--no-gateway`, `--gateway-port`, and conflicting gateway flag validation on the easy launch surface.
- [x] 3.2 Add automated coverage for gateway auto-attach failure after session startup to verify preserved session availability plus explicit error reporting.
- [x] 3.3 Update the easy specialist and CLI reference docs to describe the new default gateway behavior, `--no-gateway`, and per-launch `--gateway-port`.
