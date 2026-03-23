## 1. Shared Gateway Mailbox State Surface

- [x] 1.1 Add the shared gateway mailbox state-update contract for `POST /v1/mail/state`, including strict request and response models for one opaque `message_ref` target plus explicit read mutation, client wiring, service routing, and loopback-only availability behavior.
- [x] 1.2 Extend the `GatewayMailboxAdapter` protocol with an explicit single-message read-state update method and implement opaque-`message_ref` read-state updates for the filesystem and Stalwart transports.
- [x] 1.3 Add focused unit and integration coverage for gateway-side read-state updates so shared mailbox state can be changed without using terminal-mutating requests, including rejection of unsupported mailbox-state fields and confirmation of the minimal acknowledgment contract.

## 2. Gateway-First Notifier And Skill Behavior

- [x] 2.1 Update projected filesystem and Stalwart mailbox system skills so attached sessions present a gateway-first routine-actions section for `check`, `send`, `reply`, and `POST /v1/mail/state`, while preserving explicit transport-local fallback sections.
- [x] 2.2 Update gateway mail notifier prompt generation and prompt-input data so wake-up turns nominate the oldest actionable unread target by shared mailbox reference, include thread, sender, subject, and remaining-unread context, preserve full-unread-set dedup semantics, and stay transport-neutral.
- [x] 2.3 Add notifier and projected-skill tests that verify bounded wake-up prompts no longer require filesystem helper reconstruction during ordinary attached-session turns, preserve dedup behavior across prompt rewrites, and keep nomination order deterministic.

## 3. Ping-Pong Demo Pack Updates

- [x] 3.1 Update the ping-pong kickoff prompt, notifier-driven turn expectations, and tracked role overlays so they carry thread and round policy without restating direct filesystem helper recipes for attached gateway runs.
- [x] 3.2 Update the demo pack implementation and automated verification to use the gateway-first mailbox flow for kickoff, reply, and read-state completion.
- [x] 3.3 Add or refresh demo-focused tests to cover the responder bounded-turn path that replies in-thread, marks the source message read after success, and stops cleanly.

## 4. Documentation And Final Verification

- [x] 4.1 Update gateway and mailbox contract docs to describe the new shared mailbox state-update route, its route-table entry, its minimal acknowledgment contract, and the notifier nomination and deduplication rules.
- [x] 4.2 Update workflow and demo guidance to describe gateway-first attached-session mailbox behavior for both transports and fallback-only direct helper usage.
- [x] 4.3 Run the focused unit, integration, and demo-pack verification commands needed to prove the gateway-first bounded mailbox-turn path works end to end.
