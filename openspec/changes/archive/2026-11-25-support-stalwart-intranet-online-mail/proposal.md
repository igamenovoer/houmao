# Proposal

## Why

Intranet Stalwart deployments can advertise a JMAP origin that Houmao cannot approve through its operator controls. Account provisioning also stops at principal creation, so the live mail suite had to rewrite discovery and initialize missing JMAP resources before an agent could send and archive. [Issue #98](https://github.com/igamenovoer/houmao/issues/98)

## What Changes

- Let the operator approve exact JMAP origins for the selected online binding. Use HTTPS or loopback HTTP by default, and show approved origins and plaintext use in owner status.
- Use standard JMAP discovery for base-URL inputs in both live attach and administrative launch. Validate the advertised API and upload endpoints against the binding's connection policy.
- **BREAKING** Require Stalwart mailboxes to pass Inbox, Sent, and Archive readiness checks at activation and revalidation. Explicit provisioning ensures the requested sending identity and Archive role and returns the verified account, identity, and role IDs.
- Make bundled Stalwart advertise the published loopback JMAP origin. Document a dedicated JMAP test domain while retaining the seeded Cypht accounts on `houmao.localhost`.
- Exercise the product provisioner and direct JMAP attachment in both instructional mail cases. Verify reply delivery, archive state, and cleanup of run-owned accounts.

## Capabilities

### New Capabilities

### Modified Capabilities

- `online-mail-attachment` defines binding-scoped origin approval, owner diagnostics, and mailbox readiness before activation.
- `agent-mailbox-stalwart-transport` defines origin and redirect checks, standard discovery, and send-capable provisioning.
- `houmao-srv-ctrl-native-cli` specifies the repeatable attach option and actionable errors for origin and readiness failures.
- `email-system-docker-stack` specifies the advertised loopback JMAP origin and the local account setup guidance.

## Impact

The change spans the Stalwart client, online attachment request and status, launch declarations, and online binding persistence. It updates the stack configuration and setup guides. The instructional mail suite will use the shared provisioner and supported attach command against an explicitly selected provider. [Mailbox implementation](../../../src/houmao/mailbox/) · [Local stack](../../../dockers/email-system/)
