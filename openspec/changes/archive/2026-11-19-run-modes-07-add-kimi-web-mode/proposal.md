# Proposal

## Why

Kimi Web lets a person and a program work in the same conversation. Houmao needs to supervise the native host, inspect its readiness immediately before managed input, and represent the outcome Kimi actually returns.

## What Changes

- Add `(kimi, web)` for Kimi Code `2.6.0` using `kimi web --no-open`, a private home, an authenticated loopback host, and an exact native session.
- Apply the TUI readiness policy to ordinary manager, gateway, mail, and plugin prompts. Serialize Houmao writers and check readiness immediately before the native POST.
- Preserve queued, running, settled, and uncertain outcomes. A browser submission that lands after the final check can cause Kimi to queue the managed prompt.
- Keep browser and gateway access independent. Support exact prompt interruption, gateway reattachment, owner stop, and explicit native-session resume.

## Capabilities

### New Capabilities

- `kimi-web-control` defines the owned Kimi browser host, readiness checks, shared observation, and lifecycle.

### Modified Capabilities

None.

## Impact

Extends Web launch selection, gateway and passive observation, and browser fixtures. Qualification covers the stock Kimi Code `2.6.0` API with self-hosted `Qwen/Qwen3.8-27B-FP8`.

## Dependencies

Requires `run-modes-02-unify-managed-agent-control`. Reuses the current managed identity and lifecycle shipped by the preceding run-mode changes.
