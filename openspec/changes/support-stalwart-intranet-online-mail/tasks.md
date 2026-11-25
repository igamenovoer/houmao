# Tasks

## 1. JMAP Connection Policy

- [x] 1.1 Normalize explicit JMAP origins and enforce the binding's discovery, API, upload, and redirect policy. Extend the wire tests to cover default HTTPS and loopback behavior, approved intranet HTTP and cross-origin endpoints, malformed approvals, scheme and port mismatches, same-origin discovery redirects, and rejected POST redirects. Assert that rejected targets receive zero requests.
- [x] 1.2 Use shared `/.well-known/jmap` derivation for base-URL live attach and administrative launch. Verify both entry points reach session discovery and preserve an explicit discovery URL. Update the JMAP client reference with the endpoint and origin rules.

## 2. Binding Authority and Operator Controls

- [x] 2.1 Add `trusted_jmap_origins` to the attach request, `mailboxes.online` declaration, and resolved manifest. Feed the policy into attachment validation, gateway and notifier connections, and the direct mail adapter. Test a manifest round trip, an older manifest using defaults, and use of the same policy after refresh, reconnect, and client reconstruction.
- [x] 2.2 Persist the verified API origin with the account and identity pins. Test same-scope approval updates, revision conflicts, rejection of an API-origin change during revalidation, and explicit replacement with a new binding ID. Assert that a changed origin receives zero method requests from the old binding.
- [x] 2.3 Add repeatable `--trust-jmap-origin` to scoped attach and expose safe origin details and the plaintext warning in owner status. Verify the CLI and API request, status, and origin error paths, including the passive-server proxy and the registry's credential-free projection. Document the option, launch declaration, and replacement behavior in the CLI and Stalwart setup guides.

## 3. Send-Capable Provisioning

- [x] 3.1 Reuse a read-only readiness check for the selected account, sending identity, required mailbox roles, and rights. Test a ready account and actionable failures for missing or ambiguous identities, missing roles, and denied rights. Verify failed attach and revalidation preserve the configured scope and use only discovery and read methods.
- [x] 3.2 Preflight unsupported domains and discovery policy before management writes. Reconcile the selected principal and its canonical login with private, retryable credential storage. Extend provisioning tests for `.localhost` and `.test`, a conflicting existing principal, and an interrupted account creation retried with the same credential.
- [x] 3.3 Ensure the matching identity and Archive role under normal mailbox credentials during explicit provisioning. Verify provider readback, return account, identity, origin, and role IDs, and populate the launch binding pins. Test that repeat provisioning preserves IDs and credentials and that provider refusal surfaces an actionable error. Document the domain and role prerequisites and repair steps for existing accounts.

## 4. Bundled Development Stack

- [x] 4.1 Configure the JMAP session response to advertise the published loopback origin and add the discovery check to `dockers/email-system/verify.sh`. Check the default configuration, then exercise fresh bring-up with a disposable Compose project and a free custom HTTP port. Verify the advertised API and upload origins, Webadmin access, and the seeded Cypht and SMTP/IMAP workflows.
- [x] 4.2 Document the direct JMAP setup with an explicitly selected send-capable sandbox domain. Walk through the guide against the disposable stack, including first-time account provisioning and use of the default origin policy.

## 5. Product Path Verification

- [x] 5.1 Replace the instructional proxy and raw JMAP resource creation with the shared provisioner and normal attach. Update the case setup and evidence instructions. Verify explicit admin credential selection, the existing-domain constraint, direct discovery, and cleanup by canonical principal name with absence confirmed for run-owned accounts.
- [x] 5.2 Exercise the supported provisioning and attach paths against disposable Stalwart in the mailbox integration suite. Verify normal gateway and direct operations, refresh and reconnect, and account readiness on a real provider. Run the focused mailbox, runtime, CLI, and gateway tests in Pixi.
- [x] 5.3 Run both instructional cases with an explicitly selected model fixture, isolated tmux servers, and disposable Stalwart accounts. Record provider evidence for notifier wake, send, threaded reply, and archive, plus cleanup. Confirm both cases use direct JMAP and the product provisioner.
