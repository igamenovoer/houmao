## Why

The current headless mail ping-pong demo exposes a product gap in bounded mailbox turns. Although the repository already documents the live gateway mailbox facade as the preferred shared mailbox surface when it is attached, filesystem-backed headless turns still fall back to reconstructing low-level transport details inside the agent turn. That makes kickoff and wake-up turns spend their budget rediscovering `deliver_message.py`, threading fields, and read-state mechanics instead of performing one bounded mailbox action.

This gap now blocks the unattended gateway-driven demo from being reliable. The fix should move routine mailbox work back onto product-owned gateway and runtime contracts so demo roles stay policy-thin and transport details remain implementation-owned.

## What Changes

- Make attached-session routine mailbox work gateway-first for bounded agent turns, including the filesystem transport, instead of relying on agents to reconstruct direct filesystem delivery steps during normal send or reply flows.
- Extend the shared gateway mailbox facade with one gateway-owned single-target read-state update route so an agent can complete the routine "process one unread message" path without transport-specific reasoning after a successful reply or follow-up send.
- Refine the gateway mail notifier contract so wake-up prompts describe one actionable mailbox task rooted in shared mailbox references rather than only a generic unread digest.
- Tighten the projected mailbox system skills so filesystem and Stalwart sessions treat gateway-first routine actions as the default attached-session path, with direct transport-specific helpers reserved for fallback when no live gateway mailbox facade is available or when an operation falls outside the shared facade.
- Update the mail ping-pong gateway demo pack so kickoff and later wake-up turns rely on the gateway-first shared mailbox contract instead of low-level filesystem transport reconstruction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: extend the shared `/v1/mail/*` facade so routine mailbox handling can complete through gateway-owned shared operations, including one single-target read-state mutation after successful processing.
- `agent-gateway-mail-notifier`: change notifier wake-up behavior from a generic unread reminder into an actionable shared-mailbox task contract suitable for bounded headless turns.
- `agent-mailbox-protocol`: extend the shared mailbox operation contract so mailbox state mutation can target one opaque shared message reference without requiring transport-local identifiers or broader mailbox-flag editing in this change.
- `agent-mailbox-system-skills`: require projected mailbox skills for both filesystem and Stalwart transports to treat the live gateway facade as the default routine path for shared mailbox operations when attached, with direct transport-specific helpers reserved for fallback or transport-only work.
- `mail-ping-pong-gateway-demo-pack`: require the tracked demo to use the gateway-first bounded mailbox-turn contract for kickoff and later notifier-driven turns.

## Impact

- Affected code: gateway mailbox models, gateway service routes, gateway mailbox adapters, projected filesystem and Stalwart mailbox system skills, and the mail ping-pong demo pack runner and role fixtures.
- Affected APIs: gateway shared mailbox HTTP surface under `/v1/mail/*` including `POST /v1/mail/state`, notifier prompt contract, and the projected mailbox skill contract for attached sessions. This change does not add a new runtime `mail state` CLI surface.
- Affected systems: filesystem mailbox transport, gateway mail notifier, managed headless mailbox demos, and shared mailbox documentation/tests around gateway-first behavior.
