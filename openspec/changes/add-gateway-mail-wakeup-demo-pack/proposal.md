## Why

The repository now has a live gateway mail notifier, but it does not yet provide one self-contained, reproducible demo pack that shows the notifier noticing unread filesystem mail, deciding whether to wake a managed agent, and leaving a clear audit trail for skipped versus delivered wake-up decisions. That gap makes it hard to validate the current unread-set wake-up contract end to end, especially for manual mail injection, busy-session deferral, and burst-delivery scenarios.

## What Changes

- Add a new self-contained tutorial pack under `scripts/demo/` that demonstrates gateway-driven mailbox wake-up flows against a live CAO-backed session, with both automatic and manual operator paths.
- Teach and verify the current notifier contract as unread-set based rather than per-message notification based: the gateway wakes the agent when unread mail exists and the session is eligible, and one reminder prompt may summarize multiple unread messages.
- Add an automatic scenario that waits for an idle session, injects one email that instructs the agent to write the current time to a tracked output file, and verifies that the wake-up path and resulting artifact are observable.
- Add manual scenarios that let an operator inject one email from inline text or a body file, inject multiple emails in quick succession, and inspect the resulting wake-up behavior, mailbox state, gateway state, and output artifacts.
- Strengthen gateway notifier observability so each poll cycle records queryable decision history in a dedicated `queue.sqlite` audit table, while keeping `/v1/mail-notifier` as a compact status snapshot and `events.jsonl` focused on request lifecycle.
- Keep the new pack self-contained for v1 with pack-local helpers, and make the golden report compare sanitized notifier outcome summaries rather than exact per-poll sequences.

## Capabilities

### New Capabilities
- `gateway-mail-wakeup-demo-pack`: Defines the repository-owned tutorial pack that demonstrates and verifies gateway-managed mailbox wake-up behavior under `scripts/demo/`.

### Modified Capabilities
- `agent-gateway`: Extend gateway requirements so notifier wake-up semantics are explicitly unread-set based and gateway-owned notifier polling records detailed decision outcomes suitable for operator review and demo verification.

## Impact

- Affected code: `scripts/demo/gateway-mail-wakeup-demo-pack/*`, `scripts/demo/gateway-mail-wakeup-demo-pack/scripts/*`, `src/houmao/agents/realm_controller/gateway_service.py`, and `src/houmao/agents/realm_controller/gateway_storage.py`.
- Affected docs: gateway reference pages, tutorial-pack README links, and any operator guidance that needs to distinguish unread-set wake-up behavior from per-message notification behavior.
- Affected tests: gateway notifier unit or integration coverage, demo-pack verification helpers, and any automated coverage needed for detailed notifier-decision auditing.
