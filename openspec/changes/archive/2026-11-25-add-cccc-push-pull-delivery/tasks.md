# Tasks

## 1. CCCC Receiver Protocol v2

- [x] 1.1 Extend the tracked CCCC receiver patch to record ordered first-delivery work durably for each intended Actor registration. Verify provider recovery reconstructs pending entries after interrupted persistence and that busy or absent receivers, capacity limits, and expired pending work have distinct receipt outcomes.
- [x] 1.2 Add transport-scoped receiver leases, an atomic bounded pull, and an authenticated ordered push stream with credit. Exercise the actual provider for snapshot timing, original timestamps, count and byte bounds, stream backpressure, repeated frames, and lease exclusion between gateway and direct clients.
- [x] 1.3 Implement exact-batch start, pre-handoff deferral, and atomic settlement. Verify current-generation and start-ID fencing, repeated requests, conflicting batch membership, and crash or takeover recovery for unstarted, confirmed, and uncertain attempts in `tests/integration/cccc/test_receiver_recovery.py`.
- [x] 1.4 Add temporary direct pull claims and expiring exact-batch acknowledgments. Verify the same Actor can acknowledge after lease release, other Actors and generations cannot use the receipt, and expired unacknowledged exposure is uncertain. Verify direct references resolve the original event and authority is restricted to advertised Actor-scoped CCCC operations.
- [x] 1.5 Route typed Mail notices through independent intake credit or notice pulls while keeping the qualified Mail cursor and receipt operations available. Exercise notice admission during chat backpressure and the existing actual-provider Mail and crash recovery tests.
- [x] 1.6 Update `extern/tracked/cccc-receiver/upstream.json`, the protocol reference, and `tools/cccc` preparation and provisioning for v2. Verify the documented Pixi flow builds the pinned service from a fresh prepared checkout and that stock or incompatible services report explicit capability errors.

## 2. Gateway SDK and Delivery Configuration

- [x] 2.1 Add a lifecycle-fenced ordinary readiness observation to the public plugin SDK. Exercise body replacement, context revocation, busy transitions, and late ready-only refusal in the gateway host and support tests.
- [x] 2.2 Add the trusted header and host-owned request fence for projected ordinary events. Verify the header uses host and validated binding context, one fence contains the complete projection, and the encoded size check covers both. Exercise internal correlation omission and escaping of sender and body text that resembles header fields, controls, or fence delimiters. Document how a plugin selects the presentation.
- [x] 2.3 Add the v2 RPC and stream client in `houmao-cccc`. Update package compatibility metadata and test endpoint and Actor authority, finite stream and response limits, and error classification without exposing credentials.
- [x] 2.4 Implement the per-instance `houmao-mgr` launch override and authorized `GET` and `PUT` delivery settings. Verify startup defaults and precedence, instance isolation, authorization, validation, conflicting revisions, and desired/effective transition status. Document launch and live configuration in the CCCC gateway guide.

## 3. Gateway Scheduling and Chat Access

- [x] 3.1 Implement scheduled pull, push ASAP, and timed push batching with deterministic clock and readiness tests. Verify one batch for each non-empty pull, FIFO ASAP waits, quiet and maximum deadlines, exact boundary arrivals, duplicates, full staging, and separate immediate admission for Mail notices.
- [x] 3.2 Connect sealed chat batches to ready-only dispatch and exact per-message provider settlement. Verify a native queued receipt awaits evidence for its exact prompt, a definitive pre-handoff readiness loss defers the same batch, and an uncertain handoff produces no automatic replay.
- [x] 3.3 Supervise workers and rotate intake ownership during mode changes, reconnect, and shutdown. Verify policy edits seal the open batch, transport switches drain or classify active handoff and fence old workers, and the replacement can recover CCCC-owned pending work using a new lease.
- [x] 3.4 Implement the CCCC request presentation and scoped short handles for exact detail, history selection, and reply. Verify the header shows the bound self Group and Actor, the resolved gateway base URL once, the selected instance's three relative API paths, and the reply fields. Verify single deliveries and mixed-sender batches use one fence and retain order and attribution. Exercise exact-parent replies, duplicate operations, expiry, restart, and cross-scope attempts.
- [x] 3.5 Derive common gateway send and reply authority from the selected plugin binding and expose authorized CCCC discovery. Verify a short connection token detects stale recipient selection and discovery discloses only the scoped routing descriptors and capabilities. Document the gateway facade, handle-based chat, and advanced direct calls in the CCCC guide and agent instructions.

## 4. Direct CLI and Mail

- [x] 4.1 Add verified managed gateway selection and explicit direct Actor profile selection to `houmao-cccc`. Exercise nondefault instances, explicit HTTPS gateway selection, owner and profile mismatches, invalid configuration, and gateway authorization or uncertain mutation errors without a second provider mutation.
- [x] 4.2 Route qualified common chat operations, discovery, ordered pull, and direct acknowledgment through the provider client. Verify a gatewayless pull produces one ordered result, replies can use scoped references from a later invocation, and competing intake reports a lease conflict. Document the profile, pull, receipt, reply, and advanced native call workflow.
- [x] 4.3 Share qualified Mail operation handling between gateway and direct mode. Exercise read preconditions, operation-ID reconciliation, offline and online email independence, and direct failures against the existing `test_cccc_mail.py` and installed Mail qualification. Document direct Mail usage and its receipt handling.

## 5. End-to-End Qualification

- [x] 5.1 Update the provider, installed-wheel, and instructional CCCC scenarios that assume immediate busy refusal or that all prior offers are ineligible after reconnect. Run the compatible provider and independently installed wheels through scheduled pull, push ASAP, push batching, live transport changes, restart recovery, direct CLI operation, and Mail coexistence. Verify handoff receipts and record version and patch identity in the acceptance map.
- [x] 5.2 Exercise two real managed coding agents with the maintained CCCC fixture and an explicitly selected client and model. Verify one request fence around the compact ordered batch, per-message native reply ancestry, and exact handoff receipts. Report real-agent evidence independently of the deterministic and installed runs.
