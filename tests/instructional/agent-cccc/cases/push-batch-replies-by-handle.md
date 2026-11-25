# Push Batches Preserve Reply Ancestry

Agent A sends two CCCC requests back to back. Agent B receives an ordered list in one native prompt and replies separately to each request.

## Drive

Run Doctor and select two distinct neutral markers `TOKEN_FIRST` and `TOKEN_SECOND`. Use a fresh `CASE_EVIDENCE="$EVIDENCE/push-batch-replies-by-handle"` directory. Give B an eight-second quiet interval and a twenty-second maximum wait.

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy batch \
  --quiet-interval 8 --max-wait 20 > "$CASE_EVIDENCE/delivery.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json and use CCCC chat. Send the peer two request_reply messages in immediate succession in a single shell tool call. First ask for a reply with marker $TOKEN_FIRST. Then ask for a separate reply with marker $TOKEN_SECOND. Use a fresh operation ID for each send. Finish after storing both messages." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

Verify both native parents independently and compare the native prompt with the expected order.

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN_FIRST" --expected-attempts accepted \
  > "$CASE_EVIDENCE/first-reply.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN_SECOND" --expected-attempts accepted \
  > "$CASE_EVIDENCE/second-reply.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN_FIRST" "$TOKEN_SECOND" \
  > "$CASE_EVIDENCE/native-batch.json"
```

## Evidence

Capture both native transcripts, provider history and deliveries, and the channel audit. Require one native request fence containing both requests in the supplied order. Verify a distinct handle, CCCC timestamp, and correct sender on each entry. Require one accepted handoff and one agent-authored reply with exact original-event ancestry for each request.
