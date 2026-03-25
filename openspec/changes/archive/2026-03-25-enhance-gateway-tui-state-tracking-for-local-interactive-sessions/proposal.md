## Why

Attached gateways for runtime-owned `local_interactive` sessions already support prompt delivery, interrupt delivery, and general health inspection, but they still fail closed on the gateway-owned TUI tracking surface. That leaves a visible control-plane gap for the same attached session and prevents local interactive workflows from relying on the gateway as the single live source for TUI state, TUI history, and explicit prompt-submission evidence.

## What Changes

- Enable the gateway to start its existing gateway-owned TUI tracking runtime for attached runtime-owned `local_interactive` sessions when the attach contract already provides sufficient runtime and tmux identity.
- Allow the existing gateway-local TUI tracking routes to succeed for attached `local_interactive` sessions, including current state, recent history, and explicit prompt-note tracking.
- Keep the change scoped to the runtime-owned gateway path and preserve the current attach-contract shape; do not require `houmao-server` admission, discovery, or projection changes for this enhancement.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `agent-gateway`: extend the per-agent gateway contract so an attached gateway for a runtime-owned `local_interactive` session can expose gateway-owned TUI tracking state, history, and explicit prompt-submission evidence instead of treating that backend as unsupported for live TUI tracking routes.
- `official-tui-state-tracking`: clarify that the attached gateway may remain the authoritative live tracking owner for runtime-owned `local_interactive` TUI sessions outside `houmao-server`, including ownership of explicit prompt-submission evidence forwarded through the gateway.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_service.py` and nearby gateway/runtime support code that derives tracked-session identity for attached sessions.
- Affected behavior: `GET /v1/control/tui/state`, `GET /v1/control/tui/history`, and gateway-owned prompt-note tracking for attached runtime-owned `local_interactive` sessions.
- Validation: add automated coverage for attached `local_interactive` gateway tracking without involving `houmao-server`.
