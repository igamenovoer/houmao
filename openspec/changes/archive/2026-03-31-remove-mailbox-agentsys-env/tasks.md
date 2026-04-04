## 1. Runtime Mailbox Authority

- [x] 1.1 Refactor mailbox runtime helpers so current mailbox resolution derives actionable filesystem or Stalwart state from the persisted session mailbox binding instead of `AGENTSYS_MAILBOX_*` env.
- [x] 1.2 Remove mailbox-specific env generation, tmux mailbox projection, and `mailbox_live_*` launch-plan metadata from launch-plan assembly and runtime mailbox mutation flows while preserving manifest-backed mailbox persistence and non-mailbox tmux discovery pointers.
- [x] 1.3 Update `houmao-mgr agents mail resolve-live` on both local and pair-backed paths to return structured JSON-backed mailbox discovery without mailbox `env` payloads or mailbox shell-export output.

## 2. Mailbox Workflows

- [x] 2.1 Update `houmao-mgr agents mailbox register`, `status`, and `unregister` to compute mailbox activation from durable binding plus transport validation and remove residual `pending_relaunch` or `relaunch_required` outputs.
- [x] 2.2 Update `houmao-mgr agents mail` readiness checks and gateway mail-notifier readiness to use manifest-backed mailbox resolution rather than mailbox env or mailbox-specific tmux projection.
- [x] 2.3 Preserve filesystem mailbox root selection and active-registration path derivation for current mailbox work after mailbox env removal.

## 3. Skills And Docs

- [x] 3.1 Update runtime-owned mailbox skill assets, helper references, and prompts to consume `houmao-mgr agents mail resolve-live` structured output and stop referencing `AGENTSYS_MAILBOX_*`.
- [x] 3.2 Update mailbox, gateway, system-files, and CLI reference docs to describe the manifest-first, resolver-first mailbox contract and remove mailbox shell-export or mailbox-env guidance.

## 4. Verification

- [x] 4.1 Replace unit and integration tests that assert mailbox env bindings, tmux mailbox projection refresh, or resolver shell-export output with manifest-backed and resolver-JSON assertions.
- [x] 4.2 Run targeted mailbox runtime, managed-agent mailbox, gateway notifier, and CLI-shape test coverage to verify the new contract end to end.
