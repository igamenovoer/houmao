# Tasks

## 1. Establish Prerequisites and Durable Package Boundaries

- [x] 1.1 Verify the completed gateway plugin API is implemented and synchronize its specs if needed; verify main specs contain the SDK, immediate refusal, no-resend, and gateway-only restart requirements before proceeding.
- [x] 1.2 Add the optional `packages/houmao-cccc/` distribution, public-SDK-only entry point, declared compatibility range, and thin CLI entry point; verify an independently built wheel installs without changing core Houmao files.
- [x] 1.3 Classify the new distro location in repository guidance and include its Python source in contributor formatting, lint, typing, and relevant test commands; verify core wheel/sdist inventories still exclude the optional distribution and development tooling.
- [x] 1.4 Add a durable CCCC dependency manifest and reviewed patch-series layout under `extern/tracked/cccc-receiver/`, or pin an equivalent qualified upstream revision; verify a clean prepared checkout reproduces the selected sources and license/provenance records without changes in the orphan reference.

## 2. Add Provider Actor Authority and Protocol Negotiation

- [x] 2.1 Implement the generic externally controlled Actor/receiver source in the pinned CCCC dependency; verify provider tests show Group/Actor stop and restart do not launch, stop, or reset the external body.
- [x] 2.2 Add versioned receiver binding/capability inspection and fixed-Actor bearer authentication without weakening existing Web authentication or CSRF checks; verify normal grants cannot impersonate a human, address another Group/Actor, or invoke administration.
- [x] 2.3 Add explicit administrative grant issuance/revocation for already-provisioned Actors, with private-file export and generation binding; verify recreated Actors invalidate old grants and no credential is emitted into tracked files or ordinary diagnostics.
- [x] 2.4 Document the proposed provider protocol, qualified source/patch identifiers, unsupported stock-service behavior, and administrative-versus-runtime setup boundary; verify examples use normal grants for all plugin operations.

## 3. Implement Provider Leases and Authoritative Delivery Attempts

- [x] 3.1 Implement single-receiver acquisition, renewal, expiry, and current-lease release with connection generations; verify crash replacements wait for expiry, Actor credentials cannot force takeover, and clean release permits reacquisition.
- [x] 3.2 Add count/byte/deadline-bounded single-attempt offers and provider claim-before-I/O persistence; verify duplicate polls cannot offer the same attempt concurrently and expired or oversized offers cannot produce handoff success.
- [x] 3.3 Record confirmed, refused, failed, and uncertain outcomes using authoritative CCCC receipts; verify repeated settlement is idempotent and offered-but-unsettled work becomes uncertain after receiver or daemon loss.
- [x] 3.4 Add original-sender-authorized fresh delivery retry with new attempt IDs and explicit uncertain-retry acknowledgement; verify matching send-operation reuse does not retry delivery and another Actor cannot retry an outgoing event it does not own.
- [x] 3.5 Fence external receiver attempts out of automatic reconnect/activation replay while preserving ledger retention and bounded receipt/history reconciliation; verify accepted, refused, and uncertain attempts do not reach a replacement receiver merely because it reconnects.
- [x] 3.6 Add provider protocol and failure-recovery tests with documentation of handoff versus storage acceptance and no exactly-once promise; verify restart, lost acknowledgement, stale generation, and partial-recipient evidence against the actual ledger.
- [x] 3.7 Add explicit CCCC-operator early takeover through the provider management boundary and document its authority and recovery delay; verify takeover fences old polls/outcomes, is unavailable through normal Actor grants or plugin routes, and never retries unsettled attempts.

## 4. Implement Owner-Bound Plugin Transport and References

- [x] 4.1 Implement strict endpoint/Group/Actor/generation configuration and selected private credential validation; verify missing/unsafe files, ambient credentials, URL secrets, owner mismatch, and Actor substitution are rejected without provider side effects.
- [x] 4.2 Implement the asynchronous protocol client, capability negotiation, same-binding connection state, finite timeouts, and secure endpoint policy; verify unsupported stock CCCC, protocol mismatch, redirects, and remote TLS failures produce sanitized errors.
- [x] 4.3 Implement resource-free factory construction and supervised connection/renewal workers with local epoch fencing; verify CCCC startup failure leaves core health available and connect/disconnect/reconnect/refresh cannot change immutable binding selection.
- [x] 4.4 Implement bounded scoped event/history/receipt references and restart-stable non-message state; verify cross-owner, cross-binding, Actor-recreation, query-mismatch, malformed, and tampered references fail before retrieval or mutation.
- [x] 4.5 Document package installation, private credential preparation, gateway-only attachment/reconfiguration, status meanings, and cleanup; verify documented installation and connection commands against the built wheel.

## 5. Implement Chat Operations and Immediate Gateway Handoff

- [x] 5.1 Add owner-bound send/reply operations and provider operation-ID reconciliation with normalized-request conflict detection; verify explicit recipients/modes, stable native event IDs, structured reply ancestry, and uncertain response handling without automatic mutation retry.
- [x] 5.2 Add explicit delivery retry and bounded delivery-receipt operations; verify original-sender authorization, binding preconditions, partial outcomes, and required acknowledgement before retrying an uncertain handoff.
- [x] 5.3 Add bounded non-consuming history, exact event lookup, public membership, and effective capabilities; verify provider page caps, response byte limits, stale anchors, Actor visibility, and unchanged native Mail cursor.
- [x] 5.4 Connect each current delivery offer to the public immediate dispatch port and map readiness, unavailability, invalid input, body replacement, and uncertainty to provider outcomes; verify busy refusal is immediate and no late callback or recovered worker dispatches old content.
- [x] 5.5 Publish namespaced HTTP routes and the thin CLI without core imports or body-side provider authentication; verify route staging, two-instance isolation, safe status, and control-looking peer text remaining ordinary content.
- [x] 5.6 Document send acceptance versus recipient handoff, reply obligations, explicit retries, history recovery, limits, and initial Mail unavailability; verify documented HTTP/CLI examples exercise the qualified Actor interface rather than administrator Web/MCP endpoints.

## 6. Qualify the Actual Deployment and Installed Boundary

- [x] 6.1 Extend the native Pixi tooling to prepare/build the pinned compatible CCCC source and track its revision/patch/protocol identity; verify a fresh build can run beside or explicitly replace the selected owned development service without altering unrelated runtime state.
- [x] 6.2 Add actual-provider integration tests under `tests/integration/cccc/` with two normal Actor grants and deterministic persistent stand-in bodies; verify sender isolation, live attachment preserving PID/conversation, reply threading, bounded history, busy refusal, explicit retry, and provider-authoritative receipts.
- [x] 6.3 Add crash/race qualification for gateway absence, body death/replacement, receiver and CCCC restart, lost acknowledgement, lease-expiry waiting, explicit operator takeover, credential rotation, and stale cursors; verify no event arrives after readiness returns or reconnect occurs without a fresh sender request.
- [x] 6.4 Build and install independent Houmao/plugin wheels in a clean external environment and launch both supported gateway process modes; verify no checkout imports, instance/owner isolation, ordinary admission, loopback policy, and complete worker/process cleanup.
- [x] 6.5 Publish the native deployment example, `SERVICES.md` updates, integration reference, and agent-facing CCCC usage guidance; verify commands run from a fresh documented setup and credentials/runtime state remain private and untracked.
- [x] 6.6 Add qualification tooling and a complete spec-scenario acceptance map with sanitized revision/patch/protocol evidence; verify actual-service and deterministic stand-in checks are distinguished from the required two-real-agent smoke and missing prerequisites are not counted as passing.
- [x] 6.7 Run the required small chat smoke with two real managed coding agents using the supported fixture launcher, installed Houmao/plugin distributions, distinct gateway/Actor bindings, and actual compatible CCCC; verify ordinary chat receipt and agent-authored reply ancestry, record secret-safe client/profile/result evidence, and leave #77 acceptance pending if prerequisites or execution fail.
- [x] 6.8 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, optional-package checks, affected integration/provider tests, distribution validation, and strict OpenSpec validation; verify issue #77 acceptance includes the passed two-real-agent smoke while issue #78 remains separately pending.

## Workflow Follow-Up

- Review the acceptance map and qualification evidence before synchronizing and archiving this change.
- Synchronize `cccc-gateway-binding`, `cccc-external-receiver`, and `cccc-chat` into main specs before applying `cccc-02-add-explicit-deferred-mail`.
- Update roadmap completion and close issue #77 only after implementation, deterministic/provider qualification, and the required two-real-agent chat smoke pass; this planning checklist does not mark it complete.
