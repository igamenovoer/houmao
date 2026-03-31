## 1. Runtime Mailbox Authority

- [ ] 1.1 Refactor mailbox runtime helpers so current mailbox resolution derives actionable filesystem or Stalwart state from the persisted session mailbox binding instead of `AGENTSYS_MAILBOX_*` env.
- [ ] 1.2 Remove mailbox-specific env generation and tmux mailbox projection from launch-plan assembly and runtime mailbox mutation flows while preserving manifest-backed mailbox persistence and non-mailbox tmux discovery pointers.
- [ ] 1.3 Update `houmao-mgr agents mail resolve-live` to return structured JSON-backed mailbox discovery without mailbox shell-export output.

## 2. Mailbox Workflows

- [ ] 2.1 Update `houmao-mgr agents mailbox register`, `status`, and `unregister` to compute mailbox activation from durable binding plus transport validation and remove `pending_relaunch`.
- [ ] 2.2 Update `houmao-mgr agents mail` readiness checks and gateway mail-notifier readiness to use manifest-backed mailbox resolution rather than mailbox env or mailbox-specific tmux projection.
- [ ] 2.3 Preserve filesystem mailbox root selection and active-registration path derivation for current mailbox work after mailbox env removal.

## 3. Skills And Docs

- [ ] 3.1 Update runtime-owned mailbox skill assets, helper references, and prompts to consume `houmao-mgr agents mail resolve-live` structured output and stop referencing `AGENTSYS_MAILBOX_*`.
- [ ] 3.2 Update mailbox and CLI reference docs to describe the manifest-first, resolver-first mailbox contract and remove mailbox shell-export guidance.

## 4. Verification

- [ ] 4.1 Replace unit and integration tests that assert mailbox env bindings, tmux mailbox projection refresh, or resolver shell-export output with manifest-backed and resolver-JSON assertions.
- [ ] 4.2 Run targeted mailbox runtime, managed-agent mailbox, gateway notifier, and CLI-shape test coverage to verify the new contract end to end.
