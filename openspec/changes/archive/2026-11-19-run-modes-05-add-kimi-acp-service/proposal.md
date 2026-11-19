# Proposal

## Why

Kimi exposes ACP over stdio and maintains live native sessions behind that connection. Houmao currently manages Kimi's one-shot CLI and terminal UI, so callers cannot select this persistent path through the shared control API.

## What Changes

- Register `(kimi, service)` with `kimi_acp` under the service owner and request admission implemented in 04.
- Qualify the installed Kimi `2.6.0` binary. Negotiate its ACP capabilities, bind the private home, workspace and exact session, and handle reverse requests while a prompt is running.
- Tie managed results to the correlated prompt response and the exact native journal interval. Preserve replay, activity and accounting boundaries across reconnect and relaunch.
- Qualify manager and gateway lifecycle, mail or plugin wakeup, scoped cancellation, reconnect, and exact recovery on the same service. Report only supported session operations.

## Capabilities

### New Capabilities

- `kimi-acp-service-control` defines managed Kimi ACP launch, negotiated operations, session continuity, and conformance.

### Modified Capabilities

None.

## Impact

Extends Kimi launch policy, runtime adapter registration, the fixture matrix, and operator documentation. The provider binary comes from an explicitly selected installation.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-04-add-persistent-service-runtime`. Implementation precedes review of 06 in this rollout. Kimi Web has its own qualification.
