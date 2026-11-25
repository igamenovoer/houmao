# Design

## Context

The [proposal](proposal.md) revises peer roles and assigns filtering to the mail backend. The [gateway authorizer](../../../src/houmao/gateway/authorization.py) currently suppresses ordinary fallback through a retained built-in peer assignment. [Offline publication](../../../src/houmao/mailbox/managed.py) consults the recipient’s gateway policy and uses its result to select a sender-envelope check. [Online binding operations](../../../src/houmao/mailbox/online_binding.py) use a separate roster-mode guard in addition to their account and revision fences.

The [offline registry](../../../src/houmao/mailbox/registry.py) and local callers share the filesystem publisher. That publisher already resolves the sender and recipient registrations and commits mailbox projections. The [notifier](../../../src/houmao/agents/realm_controller/gateway_service.py) consumes Inbox metadata through bounded online sync or offline pages.

## Goals / Non-Goals

**Goals**

- Support verified status-only access using the existing exact grant, with an independently inspectable fallback decision for that principal.
- Keep peer roles and grants private and apply independently authorized recipient mail rules at the selected backend.
- File new blocked mail directly into Archive even when the recipient gateway is stopped.

**Non-Goals**

- New mail providers, general-purpose provider administration, or changes to CCCC delivery.
- Permanent deletion or message-body classification.

## Decisions

### Retire the Observer Tier and Make Fallback Explicit

Keep the cumulative requester, maintainer, and operator peer roles. Requester begins with `agent.status.read` and `agent.request.submit`. Use the existing exact grants and local roles for narrower access. Give each verified principal an administrator-controlled setting that disables the target default for that principal. Existing built-in assignments also continue to suppress fallback.

Expose the setting through `PUT /v1/admin/principals/{principal_id}/default-fallback` and the matching passive and owner-local policy paths. The CLI uses `access default-fallback set PRINCIPAL enabled|disabled`. Require effective administrator authority and the exact `admin.default-fallback.set` permission on `policy`. Include the setting and its effect in `access list` and `access explain`. Bind a decision that relied on fallback to the exact default and applicable principal fallback revision. Recheck both at handoff so a disable followed by an enable cannot revive a previously authorized request. Anonymous, public, roster-key, and managed-self paths continue to follow their own precedence and current proofs.

An existing observer assignment becomes an exact status effect with the same expiry, plus an explicit record that fallback is disabled for that principal. Retain any other exact grants or role assignments, including overlapping status authority and its independent expiry. An existing observer default becomes a retained status-only effect set shown explicitly in inspection. A later default update selects one of the five remaining named groups. Migrate in one policy transaction to avoid silently granting work-request access.

### Keep Mail Transport and Gateway Authorization Independent

The sender-facing gateway authorizes the exact sending mailbox operation before submission, including existing reply, delegated sending, and attachment distinctions. For ordinary offline delivery, retain active sender and recipient registration checks and enforce verified sender/binding and staged-envelope consistency wherever the transport requires them. Move that validation out of the retired recipient-policy decision so the checks still run on managed paths. Each transport receipt describes the actual submission or publication outcome for its recipients.

Use the provider’s acceptance, refusal, or uncertainty for online sends and replies. Confirmed JMAP submission establishes provider acceptance of the submission. Recipient gateways can be stopped during delivery. Keep the original explicit channel and sender binding through failure or retry.

Remove the online roster-mode gate in first-key enrollment, binding management, direct and gateway callers, status, and notifier use. Preserve account, origin, credential, owner, binding, revision, connection epoch, and caller checks at their existing boundaries. Ordinary attachment requires normal mailbox credentials. Protected policy application has a separate authorization and capability check.

### Relay Mail Rules With Independent Owner Authorization

`POST /v1/mail/{channel}/policy/apply` relays an owner-signed, mail-only update. The signature covers the operation, backend, mailbox binding or registration, expected revision, operation ID, and exact rule content. The backend or its trusted management connector verifies the signature and current owner authority. Enrollment, rotation, and revocation use a trusted path outside gateway authority. The signing credential stays outside the gateway’s process, account, and runtime credentials. The owner can submit directly to the trusted authority or verify the applied revision and outcome there.

Keep the gateway’s retained authorization store local. The backend receives only the mail rules and authorization evidence for the selected mailbox. Matching a mail address establishes no association with a gateway principal. The backend limits rule inspection and filing outcomes to the affected mailbox’s authorized owner and trusted operators. A sender receives the transport’s normal acceptance, refusal, or uncertain result. Accepted mail shares the same sender-facing result for Inbox and Archive placement.

### Give the Backend Exclusive Placement Authority

For offline mail, use the [filesystem publisher](../../../src/houmao/mailbox/managed.py) behind the trusted registry or an equivalent independently controlled writer. The writer matches authenticated sender registration metadata against the current recipient rules before committing each recipient’s placement. Serialize applicable rule updates with publication so each delivery uses one committed revision per recipient. Keep one canonical message and commit the per-recipient index, state, and folder projections consistently. Recovery and repair preserve the recorded placement.

The writer controls the canonical store, mailbox indexes, state databases, and folder projections. Protect writes and cross-mailbox reads with filesystem and execution identity isolation. Both direct CLI and gateway runtime operations go through the trusted authority for protected bindings. Their ordinary credentials permit authorized send and work reads and can retain non-placement state operations. The backend denies rule changes, folder moves, archive calls, archived-state updates, and raw writes from those runtime identities. Shared writable roots and same-identity local publishers report protected filtering as unsupported.

For online mail, apply provider-native rules through a trusted connector with management credentials outside the gateway. The provider controls delivery and resulting folders while the gateway is down. Use the provider’s supported sender match and direct Archive filing rules. Verify that runtime credentials, including through alternate provider APIs, cannot change protected rules or placement. The connector reports unsupported if the provider cannot meet those requirements. Ordinary attachment and use remain available under the binding’s existing checks.

### Archive Matching Mail at Delivery

For each recipient, the trusted backend files matching new mail directly into that mailbox’s existing Archive folder, with no Inbox membership. The sender’s Sent copy and other recipients’ placement remain independent. An owner can review Archive through separately authorized backend access.

Rule changes take effect at backend commit and govern future delivery. Adding a block leaves existing Inbox mail in place. Removing a block lets future mail follow normal delivery and leaves prior Archive placements intact.

### Use the Backend Inbox for Agent Work

The gateway and notifier use the backend’s current Inbox and existing reminder settings. Recheck current Inbox eligibility at queued handoff and on work reads. Use the binding’s effective lifecycle capabilities in status and prompt summaries. A gateway controls the presentation and timing of its own relay and reminders. A backend receipt gives the owner an independent way to verify committed policy and placement.

On protected bindings, the agent processes and replies to Inbox mail within its ordinary permissions. The owner can archive completed Inbox mail through separately authorized backend access. Use that path in the reminder and installed skill guidance. The default `any_inbox` mode can remind again until the owner files the message. The existing `unread_only` mode limits reminders to unread Inbox mail.

## Risks / Trade-Offs

- **Retained policy could gain access during upgrade.** Verify effect equality for migrated settings, independent expiry, applicable fallback, and the identity provenance of queued requests.
- **Gateway and registry may share a deployment identity today.** Qualify protected filesystem filtering only when the trusted writer owns the store and the gateway lacks a second write path. The trusted backend and its operator can see the mailbox rules it must enforce.
- **Providers differ in filtering, folder permissions, and admin isolation.** Qualify native Archive filing before offering protected filtering. Preserve provider acceptance and uncertainty in ordinary send receipts.

## Migration Plan

1. Upgrade the retained authorization schema before serving it. Convert built-in observer references to exact effects and fallback restrictions while retaining unrelated grants, credentials, role assignments, and audit evidence. Remove `agent.mail.deliver` from effective evaluation and retire its catalog entries.
2. Preserve existing bindings and provider state. Initialize Houmao-managed rules for the exact backend binding when the owner enrolls independent authority and applies a policy.
3. Update help, skills, and operator guides to describe authority enrollment, delivery-time filing, receipt verification, trusted writer isolation, and Archive review.
4. For rollback, restore a compatible retained gateway policy backup. Preserve existing folder placements. Keep protected filesystem delivery on a writer that enforces the committed rules until the owner retires those rules.
