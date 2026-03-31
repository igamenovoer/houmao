## Why

Agents can currently approximate self-wakeup by sending mailbox work to themselves and waiting for the gateway mail notifier to nudge them. That path proves the concept, but it is indirect, mailbox-specific, and awkward for a common timer-driven behavior that should be available even when mailbox support is not involved.

## What Changes

- Add a dedicated live gateway wakeup registration surface for direct self-wakeup prompts instead of routing timer-driven self-reminders through mailbox delivery.
- Support both one-off wakeups and repeating wakeups with a predefined prompt payload.
- Keep wakeup registration and scheduling fully in memory inside the live gateway process; pending wakeups are intentionally dropped when the gateway stops or restarts.
- Allow wakeup jobs to be canceled explicitly while they remain scheduled, and stop future repetitions when a repeating wakeup is canceled.
- Keep wakeup delivery gateway-owned internal behavior rather than expanding the public terminal-mutating request-kind set beyond `submit_prompt` and `interrupt`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-gateway`: extend the gateway HTTP surface and internal timer behavior to support ephemeral one-off and repeating wakeup jobs with explicit cancellation semantics.

## Impact

- Affected code includes the gateway runtime, gateway HTTP models and client, gateway-local execution arbitration, and focused gateway unit and integration coverage.
- Affected APIs include the live gateway HTTP contract for wakeup job registration, inspection, and cancellation.
- The change is intentionally non-durable: wakeup jobs do not survive gateway shutdown or restart and do not add a new persistent queue or recovery artifact under the gateway root.
