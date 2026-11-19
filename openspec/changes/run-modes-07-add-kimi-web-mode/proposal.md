# Proposal

## Why

Kimi Web provides a human browser and a programmatic API for the same conversation. Its ordinary prompt handler can queue input while busy, which conflicts with the immediate admission Houmao promises for ordinary delivery.

## What Changes

- Add `(kimi, web)` using `kimi web --no-open`, isolated home, authenticated loopback access, and a verified native host and session binding.
- Support human and programmatic work on the same native session. Distinguish browser input, managed request receipts, queued work, and verified terminal outcomes.
- Require a native conditional submission path for ordinary gateway, mail, and plugin input. Exercise a real browser racing the gateway and gate managed support on the result.
- Preserve human interaction policy, independent client access, generation-bound interruptions, operator-controlled relaunch, and sanitized browser handoff.

## Capabilities

### New Capabilities

- `kimi-web-control` defines the owned Kimi browser host, atomic input admission, shared observation, and lifecycle.

### Modified Capabilities

None.

## Impact

Extends Web native surface validation, Kimi launch policy, gateway and passive Web adapters, AG-UI observation, and browser integration fixtures. The inspected stock prompt route alone cannot satisfy ready-only delivery.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-02-unify-managed-agent-control`. Can proceed alongside 03 and 04. Kimi Web uses its own authenticated native API and has no dependency on either ACP adapter.
