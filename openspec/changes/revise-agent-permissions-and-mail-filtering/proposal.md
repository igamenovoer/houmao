# Proposal

## Why

Houmao ties ordinary email delivery to the recipient’s gateway role, even when an external provider owns delivery. Mailbox owners need filtering that works while their gateway is down and that a compromised gateway cannot override.

## What Changes

- **BREAKING** Retire `agent-observer` from the built-in catalog and default-group choices. Keep `agent.status.read` as an exact grant and let an administrator exclude a verified principal from default permissions. Preserve the effective restrictions of existing observer assignments and defaults.
- **BREAKING** Remove the recipient gateway’s `agent.mail.deliver` gate from ordinary mail, including managed offline delivery. The transport still validates its sender and destination. Gateway operations that use a mailbox, expose private content, or control an agent keep their own permissions.
- Allow keyed gateways to attach and use externally managed online mail. Where a backend supports protected filtering, let the gateway relay independently authorized mailbox rule changes for the exact binding. Retain gateway roles and grants in gateway policy and send only the required mail rules to the trusted backend.
- The trusted filesystem registry or native online backend delivers new blocked mail directly to Archive. Rule changes apply to future delivery. Existing Inbox and Archive messages stay in place.
- Report protected filtering as unsupported when the backend cannot file matching deliveries directly to Archive with placement authority isolated from the gateway.

## Capabilities

### New Capabilities

- `gateway-recipient-mail-filtering`: Gateway relay of independently authorized sender block rules and private backend-owned Archive placement at delivery.

### Modified Capabilities

- `agent-authorization-policy`: Reduce the built-in role catalog, allow explicit-only principal access, preserve existing observer restrictions, and scope mail authority to the applicable gateway operation or transport.
- `agent-gateway`: Apply revised fallback rules to work requests and relay owner-authorized policy operations for the selected mailbox.
- `passive-server-gateway-proxy`: Update retained fallback settings through the verified passive endpoint for stopped or detached agents.
- `agent-gateway-mail-notifier`: Use the backend’s current Inbox for eligibility, compaction, and dispatch.
- `agent-mailbox-system-skills`: Keep the notifier round usable when processed-mail filing requires independent owner authority.
- `docs-gateway-mail-notifier-reference`: Document backend-owned placement and why mail filtered into Archive does not trigger Inbox reminders.
- `docs-cli-reference`: Describe how backend Inbox placement affects both notifier modes.
- `online-mail-attachment`: Permit owner-authorized attachment and use with a keyed gateway in either setup order.
- `agent-mailbox-stalwart-transport`: Codify provider submission evidence and the conditions for independently authorized native filtering.
- `agent-mailbox-fs-transport`: Commit per-recipient Inbox or Archive placement under a trusted writer with exclusive access to authoritative state.
- `offline-mail-registry`: Scope owner-authorized rules to a registration and enforce placement and receipt privacy independently of recipient gateway availability.
- `houmao-mgr-agents-scope-cli`: Expose revised policy administration and report transport outcomes for ordinary mail.
- `houmao-agent-access-skill`: Teach status-only exact access and the separation between gateway authority and mailbox filtering.
- `houmao-agent-email-comms-skill`: Route ordinary mailbox work according to the binding’s placement authority.
- `houmao-agent-gateway-skill`: Teach notifier modes for mail in the authoritative Inbox.
- `houmao-agent-messaging-skill`: Teach the distinction between typed gateway requests, ordinary email, and the recipient’s treatment of delivered mail.

## Impact

The change affects retained gateway policy, built-in role and CLI catalogs, gateway and passive API authorization, offline registry delivery, online mailbox operations, the notifier, and the operator and agent guides. Protected filesystem filtering requires a registry or equivalent writer with exclusive access to the mailbox state. Protected online filtering requires native provider controls isolated from ordinary mailbox credentials.
