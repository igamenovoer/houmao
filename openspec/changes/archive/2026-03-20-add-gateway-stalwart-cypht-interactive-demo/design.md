## Context

The repository already has the three subsystems this demo needs:

- the local Stalwart and Cypht development stack under `dockers/email-system/`,
- the `stalwart` mailbox transport for runtime-managed sessions,
- the live gateway mailbox facade and unread-mail notifier.

What does not exist yet is a single runnable surface that composes those parts into one multi-account interactive workflow. The current gateway wake-up demo pack is filesystem-backed and centers on one mailbox-enabled session plus an external injector. The current Stalwart operator docs explain how to start one Stalwart-backed session, but they do not provide a two-account, two-gateway, Cypht-observable interactive demo that can be driven for multiple turns. For this version of the change, the scope is intentionally limited to that Stalwart-backed workflow; filesystem mailbox coverage is deferred.

There is also an important contract boundary to preserve. The gateway already owns `/v1/mail/*` and `/v1/mail-notifier`, and the notifier contract is already unread-set based. This change should demonstrate that behavior, not invent a second content-delivery mechanism inside the gateway or force the gateway to mutate mailbox read state.

## Goals / Non-Goals

**Goals:**

- Add a dedicated interactive demo pack for real Stalwart-backed gateway mail flows.
- Start the repository-owned email stack as part of the demo workflow rather than treating it as an undocumented external prerequisite.
- Ensure at least two real mailbox accounts such as Alice and Bob exist and can be inspected through Cypht.
- Start two live mailbox-enabled sessions and attach one loopback gateway to each.
- Let the operator send mail from one gateway-backed session to the other, inspect unread mail through Cypht, and continue the exchange for multiple turns.
- Surface receiver-side unread message content in a stable demo-visible way using the existing gateway mailbox facade.
- Keep unread-only notifier behavior explicit: unread detection, deduplication of unchanged unread sets, no auto-read side effects.
- Capture demo-owned state and inspection artifacts so the workflow is usable both interactively and as a future regression surface.

**Non-Goals:**

- Changing the core gateway mailbox or notifier protocol.
- Adding filesystem mailbox coverage or trying to establish cross-transport demo parity.
- Making the gateway print message bodies into the managed agent TUI as a new protocol feature.
- Replacing Cypht with a Houmao-owned mailbox UI.
- Requiring one notifier prompt per delivered message.
- Creating a production-grade multi-tenant email environment; this remains a development demo built on the existing local stack.

## Decisions

### Decision 1: Add a new Stalwart-specific interactive demo pack instead of extending the filesystem wake-up pack

The new workflow should live in its own directory under `scripts/demo/`, separate from `gateway-mail-wakeup-demo-pack`.

Rationale:

- The existing pack is intentionally about filesystem-backed unread wake-up and managed delivery.
- This new workflow is about real email-system interaction through Stalwart and Cypht.
- Keeping them separate preserves a clear mental model: filesystem demo versus real-email demo.
- This version does not attempt to reconcile the two demos behind a common transport abstraction.

Alternatives considered:

- Extend the existing gateway wake-up pack. Rejected because it would mix filesystem and Stalwart assumptions and blur the operator story.
- Fold the flow into Stalwart reference docs only. Rejected because the missing piece is a runnable demo surface, not prose.

### Decision 2: Use the repository-owned email stack and provision demo accounts idempotently at demo start

The demo will bring up `dockers/email-system/` through the existing repo-owned stack scripts, then ensure demo accounts exist through `dockers/email-system/provision_stalwart.py`.

The pack should treat account provisioning as idempotent setup rather than assuming a pristine `.data/` state. At minimum it should ensure:

- `alice@example.test`
- `bob@example.test`

Each account should remain usable in Cypht with documented demo credentials.

Rationale:

- The stack already owns Stalwart, Postgres, Cypht, and the account-provisioning helper.
- Idempotent ensure-account calls are safer than requiring a destructive reset before every demo run.
- The demo should prove integration with the real stack as it exists today.

Alternatives considered:

- Hard-code pre-created accounts into the stack bootstrap only. Rejected because it would make the demo less flexible and couple general stack bootstrap to one demo.
- Require operators to provision Alice and Bob manually before each run. Rejected because the pack should be self-contained.

### Decision 3: Bind each gateway session to a real Stalwart mailbox identity using explicit address and login identity

Each demo session should use the `stalwart` transport with explicit mailbox overrides:

- Alice session: mailbox address `alice@example.test`, login identity `alice`
- Bob session: mailbox address `bob@example.test`, login identity `bob`

The demo should not rely on the transport inferring the correct login identity for pre-provisioned accounts.

Rationale:

- The Stalwart account name used for login and the mailbox address are related but distinct surfaces.
- Making login identity explicit keeps session startup stable against different account naming conventions.
- This makes the pack easier to inspect and reason about from Cypht and Stalwart admin views.

Alternatives considered:

- Use only full email addresses as the login identity. Rejected because the local provisioning helper creates principal names such as `alice` and `bob`, and the demo should not rely on alias behavior.
- Let runtime defaults derive mailbox identity automatically. Rejected because the pack is teaching a concrete multi-account mapping.

### Decision 4: Start two managed sessions and two loopback gateways, but keep message-content surfacing demo-driven rather than agent-driven

The pack should start:

- one live session plus gateway for Alice,
- one live session plus gateway for Bob.

However, “the receiver gateway prints message content” should be implemented as a demo-helper behavior built on `POST /v1/mail/check`, not as a new gateway-side push channel and not as a required model behavior inside the live agent session.

That means the demo can expose a receiver-side command such as “check unread” or “watch unread” that:

- calls the receiver gateway’s mailbox facade,
- filters unread messages,
- prints normalized message metadata and body content in a stable format.

Rationale:

- `/v1/mail/check` already returns the normalized content needed for this demo.
- This keeps the pack deterministic and avoids expanding gateway semantics.
- It also avoids turning the demo into a model-behavior test when the real system under test is gateway plus Stalwart integration.

Alternatives considered:

- Require the receiver agent itself to inspect unread mail and print content into its TUI. Rejected because that adds model nondeterminism and broadens the test target unnecessarily.
- Extend `/v1/mail-notifier` to carry full message bodies. Rejected because notifier is a wake-up control surface, not a full mailbox content feed.

### Decision 5: Cypht is the manual read-state and inspection surface between turns

The operator should use Cypht to inspect Alice and Bob mailboxes directly and to observe mailbox read-state transitions in the real email system.

The demo should explicitly teach this split:

- gateway helper commands show normalized unread content and notifier state,
- Cypht shows the actual end-user mailbox view and is the human acknowledgment surface.

Reading a message in Cypht may clear unread state, and that change should become part of the demo story rather than something hidden.

Rationale:

- The user explicitly wants to look at the accounts through Cypht.
- This demonstrates that unread truth is owned by the real mail system, not by gateway-owned bookkeeping.
- It creates a clean way to observe dedup behavior: unchanged unread sets keep deduplicating until the operator reads mail or new unread mail arrives.

Alternatives considered:

- Keep the whole demo CLI-only and omit Cypht from the main flow. Rejected because Cypht is a core part of the requested operator experience.

### Decision 6: Preserve the existing unread-set notifier contract exactly

The demo should not reinterpret notifier behavior as per-message delivery. Instead it should make the existing contract concrete in a real-email environment:

- notifier polls unread state,
- notifier can enqueue a reminder only for unread mail,
- unchanged unread sets may deduplicate,
- notifier does not mark mail read,
- new unread mail or operator-driven read-state changes can change later notifier behavior.

Rationale:

- This matches the existing gateway notifier specification.
- It avoids false failures where the system is correct but the operator expected one prompt per message.

Alternatives considered:

- Treat every delivered message as requiring its own notifier event. Rejected because that conflicts with the existing unread-set design.

### Decision 7: Use a stateful command surface centered on `start`, `send`, `check`, `inspect`, and `stop`

The demo should preserve live state across commands so the same Alice and Bob sessions and gateways can be reused over several turns.

At minimum the runner should support the equivalent of:

- `start`
- `send`
- `check`
- `inspect`
- `stop`

Optional convenience flows such as `reply-latest-unread` or `watch` are acceptable, but the minimum surface should remain small and predictable.

Rationale:

- The user wants an interactive several-turn workflow, not just a one-shot scenario.
- A small stable command set is easier to operate and easier to verify later.

Alternatives considered:

- One opaque `auto` command only. Rejected because it does not support multi-turn exploration.
- A very large CLI surface. Rejected because the pack should stay focused on a narrow gateway/email interaction story.

### Decision 8: Verification should prefer gateway-owned and stack-owned evidence over transcript text

The pack should capture structured artifacts that explain:

- email stack bring-up,
- account provisioning,
- session start,
- gateway attach,
- gateway notifier status,
- receiver-side unread check results,
- Cypht access guidance,
- any stable turn history the pack itself records.

If future automation or snapshot verification is added, the primary contract should stay on structured artifacts and normalized message results rather than exact terminal text.

Rationale:

- Gateway and mailbox behavior can be correct even when human-facing output varies.
- The change is cross-system integration, so structured artifacts are the stable truth surface.

Alternatives considered:

- Make exact terminal transcript text the primary contract. Rejected because it is too fragile for a real-email demo.

## Risks / Trade-offs

- [Risk] The demo depends on a locally working Docker stack and browser-usable Cypht instance. → Mitigation: keep stack bring-up explicit, fail fast on missing images or unhealthy services, and separate stack-health diagnostics from gateway diagnostics.
- [Risk] Shared `dockers/email-system/.data/` state can make runs interact with prior mailbox contents. → Mitigation: ensure the pack provisions accounts idempotently, document when a clean reset is useful, and keep verification focused on demo-created messages or tracked subjects.
- [Risk] Reading mail in Cypht can clear unread state earlier than a maintainer expects. → Mitigation: document Cypht as the real acknowledgment surface and make unread-only semantics explicit in README and inspect output.
- [Risk] Tying session mailbox bindings to pre-provisioned accounts can be confusing if principal id, login identity, and email address drift apart. → Mitigation: require explicit demo parameters for account name, login identity, and mailbox address for each side.
- [Risk] A future maintainer may try to turn receiver-side printing into a new gateway protocol feature. → Mitigation: keep the design explicit that printing is demo-helper behavior using the existing mailbox facade.

## Migration Plan

No runtime data migration is required. This change adds a new Stalwart-only demo pack and relies on the existing email-system stack and existing Stalwart transport behavior.

Rollout path:

1. Add the new demo pack and its helper scripts.
2. Wire the pack to the existing stack bring-up and account-provisioning helpers.
3. Add any narrow tests or verification helpers for the pack.
4. Document the operator workflow.

Rollback is straightforward:

- remove the new demo pack,
- remove any demo-specific helper coverage,
- leave the existing gateway, notifier, and email-system stack untouched.

## Open Questions

- None at this time. The main design boundary is settled: use the existing gateway mailbox facade for content checks, use Cypht for manual mailbox inspection, and keep notifier behavior unread-only within the Stalwart-backed demo flow.
