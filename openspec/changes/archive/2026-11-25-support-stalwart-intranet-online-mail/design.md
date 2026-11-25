# Design

## Context

The JMAP client has an `allowed_api_origins` constructor input, but online attach, the managed connection authority, and the direct adapter omit it. Its URL validator applies the HTTPS-or-loopback rule to every origin. The redirect handler also runs that validator on Stalwart's same-origin `/.well-known/jmap` redirect. The launch resolver currently derives `/jmap` from a base URL, which Stalwart exposes for method POSTs. [Client and redirect checks](../../../src/houmao/mailbox/stalwart.py) · [Launch resolution](../../../src/houmao/agents/mailbox_runtime_support.py)

Current attach validation checks submission, the sender identity, and Inbox access. The notifier's normal inbox query also needs the Archive role, and submission needs Sent. Provisioning returns after management principal creation, before any of those JMAP checks. [Online attachment](../../../src/houmao/mailbox/online_binding.py) · [Notifier observation](../../../src/houmao/mailbox/observation.py)

## Goals / Non-Goals

Origin approvals belong to the owner-controlled online slot and follow its revision and connection epoch. The admitted binding continues to determine account scope for message references, checkpoints, and notifier effects. The existing provider admission rules govern which agents can enable Stalwart. [Binding contract](../../specs/agent-mailbox-bindings/spec.md)

Administrative provisioning prepares the selected account. Mailbox-credential attach, refresh, and reconnect validate it. Stalwart remains the authority for mailbox objects, message delivery, and lifecycle state. [Stalwart transport contract](../../specs/agent-mailbox-stalwart-transport/spec.md)

## Decisions

### Define One Origin Policy for Every JMAP Client

Accept repeatable `--trust-jmap-origin` entries on online attach and an optional `trusted_jmap_origins` list in the API request and the `mailboxes.online` launch declaration. A declaration is sufficient for provisioning profiles. Normalize each entry to a scheme, hostname, and effective port after validating its origin syntax. Deduplicate the canonical entries. Require HTTP(S), a valid host and port, and an empty or root path. Reject user information, queries, fragments, and wildcard hosts.

The selected discovery origin is an authorized destination if it uses HTTPS or loopback HTTP. An exact approval is required for non-loopback HTTP discovery. Further exact approvals authorize the API and upload endpoints that discovery advertises outside that origin. The operator explicitly approves plaintext by supplying an HTTP origin. Querying a server for session metadata gives it no authority to approve additional origins.

Use this policy before opening a JMAP request. Validate `apiUrl` before method calls and validate `uploadUrl` when resolving the endpoints for readiness and before using an expanded upload URL. Apply the same URL validation to each discovery redirect and retain the same-origin and finite-hop checks. Reject redirected method and upload POSTs. The management transport uses its own configured endpoint and administrative authorization. Reuse standard discovery derivation for base-URL launch and attach inputs.

### Persist Approval and Pin the Provider Scope

Carry the approval list through the declarative and resolved models, the strict launch-plan payload, and its read and write paths. Live attach commits it with the slot revision. Construct JMAP clients from that binding in candidate validation, connection authority, and the direct adapter. Refresh and reconnect reuse its policy. A same-account policy update uses the existing attach commit and drains admitted work under the usual fences.

Store the normalized verified `api_origin` alongside `account_id` and `identity_id`. Account IDs are provider-scoped. An origin change can point at a different deployment with overlapping IDs, even when both origins were approved for credentials. Enforce the pin before method requests on refresh, reconnect, and client reconstruction. A caller can activate a different discovery deployment, API origin, or account through explicit replacement with a fresh binding ID. Older validated bindings imply their discovery origin because the previous product path authorized only that origin. An older unvalidated launch binding records its pin during existing first-connection validation.

Show the configured discovery origin, verified API origin, approved origins, and any plaintext approval in owner-scoped status. Reuse typed errors at the operator boundary to distinguish origin rejection, a changed pinned origin, and mailbox readiness. Report only safe origin, role, permission, or provider codes. The registry continues to use the existing identity projection. [Launch-plan payload](../../../src/houmao/agents/realm_controller/boundary_models.py) · [Connection authority](../../../src/houmao/mailbox/online_authority.py) · [CLI controls](../../../src/houmao/srv_ctrl/commands/agents/mailbox.py)

### Prepare and Verify the Mailbox During Explicit Provisioning

Check the local origin inputs and known unsupported address suffixes before provider mutation. The pinned Stalwart release validates identities against the public suffix list. Report a concrete domain correction for `.localhost` and `.test`, and use the provider's result for other domains. Read back the selected management principal and use its canonical login for the built-in directory. Keep the sending address separate, and validate an explicitly supplied login against the selected mailbox. [Stalwart identity validation](https://github.com/stalwartlabs/stalwart/blob/v0.15.5/crates/jmap/src/identity/set.rs#L64-L90) · [Address sanitizer](https://github.com/stalwartlabs/stalwart/blob/v0.15.5/crates/utils/src/lib.rs#L265-L301)

Use the explicit management credential to ensure the domain and principal. Serialize provisioning for the same account within one runtime credential store. Retain the generated credential in that private store before an attempt can commit account creation, so retry can verify a completed write after a lost response. Check that an existing principal and its addresses match the selected ownership before reusing it. Reject a conflicting account with guidance to attach it using its existing credential.

Use the normal mailbox credential for the JMAP stage. Check capabilities and read back identities and roles. Stalwart can initialize identities during `Identity/get`, so create with `Identity/set` only when the exact sender remains missing. Use `Mailbox/set` to create a missing `archive` role. Treat duplicate identities, duplicate roles, and a conflicting same-name folder as explicit conflicts. After changes, refresh provider state and confirm the validated identity, roles, and rights from the readback.

Reuse this readiness check during existing-account attach, launch activation, and later revalidation. Attachment uses discovery and validation methods. Provisioning returns the verified account, identity, API origin, and role IDs with the protected credential reference. The launch path can publish the pinned account at once. A failed readiness stage retains the retry information for the selected account and returns an actionable error. [Provisioning entry point](../../../src/houmao/mailbox/stalwart.py#L176) · [Stalwart identity initialization](https://github.com/stalwartlabs/stalwart/blob/v0.15.5/crates/jmap/src/identity/get.rs#L149-L223)

### Use Direct JMAP in the Bundled Stack and Instructional Suite

Configure Stalwart's JMAP session response with `http.url` so the API and upload URLs use the loopback host and configured HTTP port. Scope this response setting to JMAP discovery so Webadmin's browser-port workflow can use its existing HTTP behavior. Check both URLs from the host discovery endpoint as part of `verify.sh`. Retain the seed domain and mailboxes for Cypht, SMTP, and IMAP. Document a dedicated accepted domain for the JMAP test accounts. [Stack configuration](../../../dockers/email-system/stalwart/config.toml) · [Stalwart advertised URL configuration](https://github.com/stalwartlabs/stalwart/blob/v0.15.5/crates/common/src/config/network.rs#L96-L117)

Have the helper in `tests/instructional/agent-mail-stalwart/` call the shared provider provisioner for its disposable accounts. Supply explicitly chosen management authorization and domain settings. Honor the existing-domain option. Use the returned normal-account credentials and direct discovery URL for the live attach commands. Forward only the origins explicitly configured for that test provider. Reuse the helper's canonical-name and absence checks for cleanup, including after partial provisioning. [Instructional test findings](https://github.com/igamenovoer/houmao/issues/98)

## Risks / Trade-offs

- A plaintext approval exposes the mailbox credential and mail traffic to observers on that network. Use HTTPS for protected connections and identify each plaintext approval in owner status.
- Existing accounts can lack an Archive role or the rights needed for the full mail lifecycle. The operator receives the exact missing prerequisite before a new account becomes active. A failed revalidation preserves the existing slot and canonical identity.
- A provider failure can leave a principal with only some of the required resources. Private retry state and provider readback let the next run complete it. Shared resources stay under the provider administrator's control.

## Migration Plan

Existing manifests load with an empty approval list when it is absent. Existing profiles with an explicit discovery URL keep that URL. Base-URL profiles derive the standard discovery path when launched next.

For a previously attached incomplete account, prepare the missing identity or role with its administrator and reconnect. For an intended deployment-origin change, use the existing replacement control. Before reverting to a runtime that predates the new manifest fields, detach the affected online slots and recreate them using a supported endpoint on the earlier runtime.
