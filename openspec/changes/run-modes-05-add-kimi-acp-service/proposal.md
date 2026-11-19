# Proposal

## Why

Kimi exposes ACP over stdio and maintains live native sessions behind that connection. Houmao currently manages Kimi's one-shot CLI and terminal UI, so callers cannot select this persistent path through the shared control API.

## What Changes

- Register `(kimi, service)` with a `kimi_acp` adapter backed by the shared service owner.
- Negotiate the installed Kimi protocol, bind the selected private home, workspace and exact session, and service native updates and interaction requests during a prompt.
- Qualify manager and gateway lifecycle, mail or plugin wakeup, scoped cancellation, reconnect, and exact recovery on the same service. Report only supported session operations.

## Capabilities

### New Capabilities

- `kimi-acp-service-control` defines managed Kimi ACP launch, negotiated operations, session continuity, and conformance.

### Modified Capabilities

None.

## Impact

Extends Kimi launch policy, runtime adapter registration, the fixture matrix, and operator documentation. The provider binary comes from an explicitly selected installation.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-04-add-persistent-service-runtime`. Can proceed alongside 06. Kimi Web uses a different interface and has its own qualification.
