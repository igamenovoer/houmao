# Tasks

## 1. CCCC Receiver Claims and Receipts

- [x] 1.1 Extend the tracked receiver v2 patch and protocol reference with the optional `chat_gateway_queue_reads` capability and RPCs. Verify capability negotiation against the patched provider and an ordinary-delivery-only v2 provider.
- [x] 1.2 Add atomic tool-read claims for an exact ordered prefix of staged attempts under the live gateway lease. Verify count and byte limits, whole-batch grouping, stale membership and lease rejection, and that exactly one of pop and ordinary start wins for a contested head.
- [x] 1.3 Persist tool-read operation IDs, snapshot fingerprints, ordered groups, and receipts. Verify matching retries and result lookup after a lost response, restart, and lease rotation. Verify changed selections conflict and an expired result cannot claim new work under the old operation ID.
- [x] 1.4 Extend exact read acknowledgment and expiry for gateway tool receipts. Verify distinct delivery outcomes, duplicate acknowledgment, cross-Actor and cross-binding rejection, and uncertain expiry without automatic replay. Retest direct pull, ordinary handoff, and independent Mail notices.

## 2. Gateway Queue Access

- [x] 2.1 Add a bounded peek selection and delivery-change wait to the CCCC plugin. Verify request bounds, timeout and lease revocation, stable selection after appends, open timed-batch visibility, and intact pull, ASAP, and timed push boundaries.
- [x] 2.2 Share the FIFO head reservation between automatic dispatch and pop, rechecking after readiness waits. Verify each ordering of the race, pre-handoff deferral, preservation of staging credit until durable claim, and safe recovery from a canceled request or ambiguous provider response.
- [x] 2.3 Expose authorized instance routes for peek, pop, result recovery, and receipt acknowledgment. Verify independent peek and consuming permissions, capability errors, exact snapshot conflicts, and the complete response budget. Verify compact sender, timestamp, mode, text, and per-message reply handles with control-looking content treated as an ordinary CCCC request.
- [x] 2.4 Use the provider record to reconcile a gateway pop and acknowledge only its exact attempts. Verify a retry or result lookup cannot consume the next batch, and verify handles issued from a recovered result are scoped to the current gateway run. Document the per-instance routes and error behavior in the CCCC gateway guide.

## 3. Agent CLI and Guidance

- [x] 3.1 Add gateway-backed `chat peek`, `chat pop`, `chat pop-result`, and gateway-mode `chat ack` to `houmao-cccc`. Verify forwarding under verified managed-self and explicit authorized gateway selection, including a named instance, and retest Actor-profile pull and acknowledgment.
- [x] 3.2 Document both agent waiting choices and the gateway-selected pop batch in the package and agent instructions. Exercise the documented commands with a bounded wait, an exact snapshot, and an operation ID and receipt. Verify the guidance explains yielding for ordinary notification, continuing an active turn after pop, and recovering a lost result.

## 4. Integrated Qualification

- [x] 4.1 Exercise the prepared provider and independently installed gateway and CLI against scheduled pull, push ASAP, and timed push. Verify durable pop receipts and exact reply ancestry, stale/racing selections, and recovery after gateway restart using the provider and installed CCCC fixtures.
- [x] 4.2 Exercise both choices in a maintained real-agent CCCC scenario. Verify a yielded turn receives ordinary notification and a later active turn peeks for staged replies, pops one gateway-selected batch, and continues with its tool result. Verify exact receipts and reply parents and that later automatic delivery starts at the next eligible message. Record the observed results in the CCCC acceptance documentation.
