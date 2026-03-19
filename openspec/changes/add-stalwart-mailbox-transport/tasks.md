## 1. Transport Contract Refactor

- [ ] 1.1 Generalize mailbox runtime models, config parsing, and manifest persistence to accept `transport=stalwart` alongside the existing filesystem transport while keeping persisted mailbox payloads secret-free.
- [ ] 1.2 Add projected Stalwart mailbox system-skill assets and transport-specific `AGENTSYS_MAILBOX_EMAIL_*` binding references without regressing the existing filesystem mailbox skill set.
- [ ] 1.3 Update runtime mailbox prompt preparation, transport readiness checks, and structured result handling so mailbox prompts select the correct transport-specific mailbox skill and guidance.

## 2. Stalwart Transport Implementation

- [ ] 2.1 Add Stalwart transport configuration and runtime-managed credential-reference handling suitable for launched sessions without persisting mailbox secrets in session manifests.
- [ ] 2.2 Implement idempotent Stalwart provisioning for mailbox domains and mailbox accounts through the Stalwart management API.
- [ ] 2.3 Implement JMAP-backed mailbox helpers for `mail check`, `mail send`, `mail reply`, and mailbox read-state updates for the Stalwart transport.
- [ ] 2.4 Implement mailbox-resident welcome-thread bootstrap and rediscovery for Stalwart-backed mailboxes.

## 3. Runtime Wiring And Verification

- [ ] 3.1 Wire Stalwart mailbox startup and resume into transport-specific launch-plan env bindings and session startup readiness checks.
- [ ] 3.2 Add integration coverage for local Stalwart provisioning and live mailbox roundtrip behavior while preserving existing filesystem mailbox coverage.
- [ ] 3.3 Update mailbox reference docs and the local Stalwart runbook to separate transport-neutral mailbox semantics from filesystem-only mechanics and to document the new Stalwart-backed workflow.
