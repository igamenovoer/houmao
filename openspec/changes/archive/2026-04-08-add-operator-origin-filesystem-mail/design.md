## Context

Houmao's current mailbox model assumes that outbound mail is authored by a real mailbox principal already bound to the managed session. The canonical protocol requires a concrete sender principal and address, the filesystem gateway adapter derives that sender from the resolved mailbox binding, and the current `houmao-mgr agents mail send` operator surface is documented as "send one mailbox message for a managed agent" rather than "drop a note into the managed agent's inbox".

That model is correct for peer mailbox participation, but it is awkward for operators who want to leave a one-way instruction for an agent without provisioning a personal mailbox identity and without expecting a reply. The new feature therefore needs to add a distinct operator-origin lane without weakening sender provenance or pretending that arbitrary fake sender addresses are valid mailbox participants.

Constraints:

- The mailbox protocol must keep a real `from` principal; operator convenience must not redefine the canonical message model into an anonymous envelope.
- The filesystem transport is the only maintained mailbox-admin transport in v1; `stalwart` remains a separate mail-server-backed transport with different provisioning semantics.
- Existing `send` and `reply` behavior must continue to mean "participate as the managed mailbox principal", not "deliver something on behalf of the operator".
- The repo already treats `HOUMAO-*` names as reserved system space; mailbox addressing should follow the same boundary.

## Goals / Non-Goals

**Goals:**

- Add a filesystem-first operator-origin mail path for leaving one-way notes in a managed agent mailbox.
- Preserve a real sender identity through a reserved Houmao-owned system mailbox principal.
- Standardize the default managed-agent mailbox address policy as `<agentname>@houmao.localhost`.
- Reserve `HOUMAO-*` mailbox local parts for Houmao-owned system principals, including `HOUMAO-operator@houmao.localhost`.
- Expose the operator-origin lane consistently through gateway, server proxy, and `houmao-mgr agents mail ...`.
- Reject reply flows against operator-origin messages instead of pretending that operator-origin mail is an ordinary conversational peer.
- Keep `stalwart` explicitly unsupported for this feature in v1.

**Non-Goals:**

- Do not make the canonical mailbox sender optional.
- Do not allow arbitrary spoofed or fake sender addresses.
- Do not overload ordinary `send` semantics with an implicit sender-mode switch.
- Do not implement Stalwart-backed operator-origin mail delivery in this change.
- Do not add a general-purpose human mailbox or reply inbox for Houmao operators.

## Decisions

### Decision: Introduce a separate operator-origin action named `post`

The new lane will be exposed as a distinct `post` action rather than as a variant of `send`.

Representative surfaces:

- `houmao-mgr agents mail post`
- `POST /v1/mail/post`
- `POST /houmao/agents/{agent_ref}/mail/post`

`send` will keep its current meaning: compose and deliver mail as the addressed managed mailbox principal. `post` will mean: deliver one operator-origin note into the addressed managed mailbox.

Rationale:

- The operator intent is different from normal mailbox participation.
- Reusing `send` with an option such as `--sender-mode operator` would blur the sender semantics and make the default path easier to misuse.
- A separate verb makes it obvious that this is mailbox delivery into the agent inbox, not agent-authored mail.

Alternatives considered:

- Overload `send` with a sender-mode flag: rejected because it weakens the semantics of ordinary `send` and makes provenance less obvious.
- Allow operator-origin mail to masquerade as ordinary `send`: rejected because the feature is specifically about preserving provenance while changing the sender identity.

### Decision: Use a reserved Houmao-owned sender identity instead of fake addresses

The system will provision one reserved filesystem mailbox principal per mailbox root:

- `principal_id = HOUMAO-operator`
- `address = HOUMAO-operator@houmao.localhost`
- `role = system_operator`

Operator-origin mail will always use that principal as the canonical sender.

Rationale:

- The existing mailbox protocol already requires a real sender principal and address.
- A reserved system principal preserves provenance and auditability without introducing anonymous or fake envelope shapes.
- Reusing the mailbox registration model keeps the feature inside the existing filesystem transport architecture.

Alternatives considered:

- Permit arbitrary fake sender addresses: rejected because it would weaken sender provenance and complicate reply, audit, and transport behavior.
- Make `from` optional in the canonical protocol: rejected because it would change the meaning of the mailbox model rather than extending it.

### Decision: Standardize default mailbox addresses as `<agentname>@houmao.localhost` and reserve `HOUMAO-*`

Newly derived managed-agent mailbox addresses will use `<agentname>@houmao.localhost`. Any local part beginning with `HOUMAO-` will be reserved for Houmao-owned system mailboxes only.

Implications:

- `research@houmao.localhost` is a valid managed-agent default.
- `HOUMAO-operator@houmao.localhost` is a valid reserved system mailbox.
- Managed agents cannot be created or rebound into a mailbox address whose local part starts with `HOUMAO-`.
- Existing explicitly configured mailbox bindings remain valid; the breaking change applies to newly derived defaults and reserved-namespace validation.

Rationale:

- Human-readable agent mailbox addresses are easier to reason about than embedding the internal `HOUMAO-` prefix in every default mailbox.
- Keeping `HOUMAO-*` reserved preserves a clear system namespace for Houmao-owned principals.

Alternatives considered:

- Keep using agent-style `HOUMAO-*` mailbox locals for all participants: rejected because it mixes system namespace and ordinary participant namespace.
- Reserve only one exact address (`HOUMAO-operator`) and allow other `HOUMAO-*` locals: rejected because it closes the door on a consistent system namespace and weakens future-proofing.

### Decision: Filesystem mailbox roots provision and protect the reserved operator account

Filesystem mailbox roots will treat the operator principal as a reserved system registration. `mailbox init` will ensure the registration exists, and `post` will also self-heal by creating or repairing that registration if the root is otherwise valid but the operator principal is missing.

The reserved operator account will be protected:

- cleanup will preserve it,
- generic unregister/purge paths will reject it by default,
- account-inspection flows may annotate it as a system account.

Rationale:

- Operator-origin delivery must not fail because the reserved system sender was never created.
- The operator account is part of the mailbox-root contract, not incidental user data.

Alternatives considered:

- Require operators to register the system sender manually: rejected because it defeats the convenience goal and creates avoidable setup failures.
- Hide the system sender from mailbox administration entirely: rejected because the account is real state and should stay inspectable even if it is protected.

### Decision: Operator-origin mail is one-way and carries explicit provenance headers

Operator-origin messages will carry explicit metadata such as:

- `x-houmao-origin: operator`
- `x-houmao-reply-policy: none`

The system will reject `reply` when the target message is operator-origin mail.

Rationale:

- The user requirement is specifically about one-way notes that do not expect replies.
- Rejecting replies is clearer than silently black-holing them into a reserved mailbox.
- The metadata gives downstream readers and tooling a stable way to identify operator-origin messages without changing the core principal model.

Alternatives considered:

- Allow replies to reach the reserved operator mailbox: rejected because it turns the feature into an operator inbox product with broader lifecycle and UX implications.
- Silently accept replies and drop them: rejected because it produces confusing behavior and hides operator intent.

### Decision: `post` requires authoritative mailbox execution and does not fall back to TUI submission

`houmao-mgr agents mail post` will use only authoritative execution paths:

- gateway-backed execution,
- pair/server-backed mail proxy execution,
- manager-owned local direct mailbox execution.

When none of those authoritative paths is available, the command will fail explicitly instead of submitting a prompt into the live agent TUI.

Rationale:

- `post` is mailbox-system behavior, not "ask the agent to send a message as itself".
- A TUI fallback would either change semantics or require the agent to impersonate the system operator mailbox.
- Explicit failure keeps the provenance contract intact.

Alternatives considered:

- Reuse the same live-TUI submission fallback as ordinary `send`: rejected because that fallback is intentionally non-authoritative and agent-mediated.

### Decision: `stalwart` remains an explicit unsupported stub in v1

The new `post` lane will support only filesystem-backed mailbox bindings in v1. When the resolved mailbox transport is `stalwart`, the operator-origin action will fail explicitly with a structured unsupported result instead of attempting partial parity.

Rationale:

- Stalwart send is tied to real mail-server account and identity provisioning, which is a separate design from filesystem mailbox registration.
- Declaring an explicit unsupported boundary is more honest than inventing a pseudo-operator sender that only works on one surface.

Alternatives considered:

- Add partial Stalwart support with ad hoc fake addresses: rejected because it breaks the real-sender principle.
- Block the proposal until Stalwart parity exists: rejected because the filesystem transport can deliver the requested operator value independently.

## Risks / Trade-offs

- [Default address change can surprise existing expectations] -> Preserve explicit existing mailbox bindings and scope the breaking change to newly derived defaults plus reserved-namespace validation.
- [Protected system account complicates mailbox-admin semantics] -> Keep it inspectable but reject generic destructive lifecycle operations against the reserved operator registration.
- [Feature spread across protocol, transport, CLI, gateway, and server layers] -> Keep `post` as a thin new lane with reused action-response shapes and explicit filesystem-only scope.
- [Filesystem-only support may look incomplete] -> Document the `stalwart` stub boundary explicitly in CLI and mailbox reference docs and return clear unsupported results.
- [Operator-origin one-way semantics could be bypassed accidentally by ordinary `send`] -> Keep `send` and `post` as separate verbs with separate route models and reply behavior.

## Migration Plan

No mailbox-corpus migration is required.

Implementation should proceed in this order:

1. add the new operator-origin capability and address-policy validation at the protocol/model boundary,
2. update filesystem mailbox bootstrap and registration rules to provision and protect `HOUMAO-operator@houmao.localhost`,
3. add gateway, server-proxy, and native CLI `post` surfaces using authoritative execution only,
4. update mailbox docs and CLI reference for the new action and reserved-address policy,
5. add targeted tests for reserved-name rejection, filesystem operator-origin delivery, reply rejection, and `stalwart` unsupported behavior.

Rollback is straightforward:

- remove the `post` surfaces,
- stop auto-provisioning the reserved operator account,
- keep existing explicitly registered mailbox addresses intact.

## Open Questions

- None for proposal scope. The design intentionally fixes the operator-origin verb as `post`, the reserved system sender as `HOUMAO-operator@houmao.localhost`, and the v1 transport boundary as filesystem-only.
