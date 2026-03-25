## Why

Runtime-owned `local_interactive` sessions already publish tmux-backed gateway capability metadata, but live gateway attach still rejects them with an unsupported-backend error. This leaves serverless local TUI agents in an inconsistent state where the runtime and persisted gateway contract say they are attachable, while the operator-facing attach path refuses to start a gateway.

## What Changes

- Enable live gateway attach for runtime-owned `local_interactive` sessions when the local tmux-backed gateway execution path is available.
- Clarify the local gateway execution adapter contract so `local_interactive` sessions are treated as a supported local tmux-backed runtime target rather than an accidental headless-only special case.
- Add regression coverage for gateway attach, status, prompt, and interrupt on runtime-owned `local_interactive` sessions.
- Update operator-facing documentation and help text to describe gateway control of supported serverless local interactive agents.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Live gateway attach for runtime-owned tmux-backed sessions must include supported `local_interactive` backends, not only REST-backed and native headless backends.
- `agent-gateway`: Gateway execution adapter support and gateway-managed prompt or interrupt delivery must explicitly cover runtime-owned `local_interactive` sessions as supported local tmux-backed targets.

## Impact

- Affected runtime and gateway code in `src/houmao/agents/realm_controller/runtime.py` and `src/houmao/agents/realm_controller/gateway_service.py`.
- Affected gateway attach contract usage in local runtime flows, plus unit and integration coverage under `tests/unit/agents/realm_controller/` and `tests/integration/agents/realm_controller/`.
- Affected operator documentation for `houmao-mgr agents gateway ...` workflows involving serverless local interactive agents.
