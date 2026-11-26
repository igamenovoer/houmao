# Push Batches Preserve Reply Ancestry

Agent A sends two CCCC requests back to back. Agent B receives an ordered list in one fenced native prompt and replies separately by handle to each request.

## Sub-cases

- `t1-batch-policy-active`: the recipient's effective delivery setting is `push` with `push_policy=batch`, `quiet_interval=8`, and `max_wait=20`.
- `t2-single-fenced-request`: two adjacent requests arrive in one native user message with one request fence in CCCC order.
- `t3-distinct-handles`: each entry has a distinct `msg_` handle, original sender, timestamp, mode, and body.
- `t4-exact-parent-replies`: the recipient authors two native `send` replies, each naming its original request as the parent.
- `t5-compact-header`: the request does not expose the binding ID, event ID, signed event reference, or connection token, and names the gateway URL once.
- `t6-no-mail-fallback`: neither agent invokes a mailbox or CCCC provider administration.

## How to get to it (user POV)

- Both agents are healthy, idle, and attached to the same CCCC Group.
- The operator selects timed batching for the recipient and chooses two distinct neutral markers.
- The operator asks Agent A to send two `request_reply` messages in immediate succession, then watches B answer each one separately.

## Driving it with cccc_lab

Preconditions:

- `RUN_META`, `EVIDENCE`, `TOKEN_FIRST`, and `TOKEN_SECOND` are set; create `CASE_EVIDENCE="$EVIDENCE/push-batch-replies-by-handle"`.
- Both agents are idle before the drive.
- Run Doctor and save the result before changing delivery policy:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
```

- **Select timed batching.** Require the requested revision to become effective:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy batch \
  --quiet-interval 8 --max-wait 20 \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Send two requests in one shell call.** Agent A must store both messages without waiting for replies:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json and use CCCC chat. Send the peer two request_reply messages in immediate succession in a single shell tool call. First ask for a reply with marker $TOKEN_FIRST. Then ask for a separate reply with marker $TOKEN_SECOND. Use a fresh operation ID for each send. Finish after storing both messages." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

- **Verify each ancestry and handoff independently.** Require one accepted handoff and one exact-parent reply for each marker:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN_FIRST" --expected-attempts accepted \
  > "$CASE_EVIDENCE/first-reply.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN_SECOND" --expected-attempts accepted \
  > "$CASE_EVIDENCE/second-reply.json"
```

- **Verify the one-fence batch and compact header.** This also requires CCCC order, original timestamps, distinct handles, and no private routing fields:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN_FIRST" "$TOKEN_SECOND" \
  > "$CASE_EVIDENCE/native-batch.json"
```

- **Capture both transcripts and provider views.** Save history, both request delivery lists, both native transcripts, and the channel audit:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" cccc \
  --run-meta "$RUN_META" --role a chat history --limit 100 \
  > "$CASE_EVIDENCE/history.json"
for SIDE in first second; do
  REF="$(jq -r '.request.event_ref' "$CASE_EVIDENCE/$SIDE-reply.json")"
  pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" cccc \
    --run-meta "$RUN_META" --role a chat deliveries --event-ref "$REF" --limit 100 \
    > "$CASE_EVIDENCE/$SIDE-deliveries.json"
done
for ROLE in a b; do
  pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" transcript \
    --run-meta "$RUN_META" --role "$ROLE" --output "$CASE_EVIDENCE" \
    > "$CASE_EVIDENCE/$ROLE-transcripts.json"
done
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" audit \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/channel-audit.json"
```

- **Proof.** Require `delivery.json` to show effective `push/batch/8/20`, `native-batch.json` to show exactly one fence with two ordered entries and distinct handles, and each reply proof to show one accepted attempt and `native_reply_ancestry` equal to its request ID. B's transcript must show two successful replies using the two handles from the fence. Keep every artifact under `CASE_EVIDENCE` and confirm it remains after cleanup.

## Gotchas

- If Agent A does not place both sends in one shell call, the requests can land in separate stable batches. Repeat the case with a fresh pair of markers rather than accepting two unrelated fences.
- If B becomes busy, the sealed batch remains pending until readiness. The receipt states still describe handoff, not completed work.
- Handles are scoped to the current gateway connection. Do not reuse a handle from an earlier run or a later reconnection.
- Batching timing uses the earlier of the shortest quiet deadline and maximum wait. The live case proves the configured effective values; deterministic timer boundaries belong to the unit suite.
- A stored event does not prove handoff. Require both accepted receipts and both exact-parent replies.
- Preserve actual failure states. Do not relabel a refused or uncertain handoff as a passing batch.

## Blinding and Transcript Checks

- Use neutral markers and ordinary work prompts; do not reveal the grading criteria to either agent.
- Grade from the fenced native request, authenticated handles, native tool calls, CCCC history, and delivery receipts, not from final assistant summaries.
- The operator prompt supplies the business intent and ordering but does not prescribe exact CCCC command lines.
