# Wait for CCCC Chat or Read It During a Turn

Agent B first finishes a turn so CCCC can notify it of later work. In a second turn, B asks its peer for two replies, waits for the gateway's sealed selection, and uses one pop result to continue the same turn. After B yields again, the next queued request arrives as an ordinary notification.

## Preconditions

Complete the bundle launch and Doctor steps with the built receiver and the matching installed CLI. Use two healthy, ready agents and their run-owned CCCC Group. Set `RUN_META`, `RUN_A`, `RUN_B`, `REPO_ROOT`, `BUNDLE_ROOT`, `EVIDENCE`, and a fresh neutral `TOKEN` as in the bundle README. The operator release file below controls B's test turn and carries no peer messages.

```bash
set -euo pipefail
export CASE_EVIDENCE="$EVIDENCE/gateway-queue-wait-and-read"
mkdir -p "$CASE_EVIDENCE"
YIELD_TOKEN="$TOKEN-yield"
FIRST_TOKEN="$TOKEN-ash"
SECOND_TOKEN="$TOKEN-pine"
NEXT_TOKEN="$TOKEN-next"
QUEUE_PROOF_DIR="$RUN_B/workdir/queue-$TOKEN"
lab() {
  local action="$1"
  shift
  pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" "$action" --run-meta "$RUN_META" "$@"
}
lab doctor > "$CASE_EVIDENCE/doctor.json"
lab cccc --role b capabilities > "$CASE_EVIDENCE/capabilities.json"
jq -e '.chat_queue == true' "$CASE_EVIDENCE/capabilities.json" >/dev/null
lab delivery --role b --policy asap > "$CASE_EVIDENCE/b-delivery.json"
lab delivery --role a --policy batch > "$CASE_EVIDENCE/a-delivery.json"
```

## Yield for Ordinary Notification

Ask B to end the turn and wait for later work. After the gateway reports that B is ready, ask A to send one request. The provider receipt and the native fence identify the same delivered message.

```bash
lab prompt --role b --prompt 'Finish this turn now. When a CCCC request arrives later, respond to its work in that new turn.' \
  > "$CASE_EVIDENCE/b-yield-prompt.json"
lab wait-execution --role b --mode ready --require-open --timeout 60 > "$CASE_EVIDENCE/b-yield-ready.json"
lab prompt --role a \
  --prompt "Use the houmao-cccc executable from cccc-brief.json. Send one CCCC request_reply asking your peer to read shared-note.txt and reply with the word it contains plus $YIELD_TOKEN. Finish after storing the request." \
  > "$CASE_EVIDENCE/a-yield-request.json"
lab verify --token "$YIELD_TOKEN" --reply-contains cobalt --expected-attempts accepted \
  > "$CASE_EVIDENCE/yield-round-trip.json"
lab verify-batch --tokens "$YIELD_TOKEN" > "$CASE_EVIDENCE/yield-native-request.json"
lab wait-execution --role a --mode ready --require-open --timeout 90 > "$CASE_EVIDENCE/a-active-ready.json"
lab wait-execution --role b --mode ready --require-open --timeout 90 > "$CASE_EVIDENCE/b-active-ready.json"
```

## Read Staged Replies During an Active Turn

B first tries a short bounded peek while its queue is empty. It then requests two peer replies in one shell call so A receives both requests together under timed batching. B uses a bounded peek with a minimum of two messages, pops its exact selection with a fresh operation ID, and acknowledges it. It looks up the operation result before using each returned handle to send an exact-parent confirmation.

Use the fixture's gateway-admitted prompt path for this long turn. The fixture waits for the exact native turn result within its configured timeout.

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prompt --run-dir "$RUN_B" --timeout 420 \
  --prompt "Use the houmao-cccc executable selected by cccc-brief.json. Remain in this one turn throughout. Create the local directory queue-$TOKEN for your tool result JSON. First run chat peek --min-messages 2 --wait-seconds 2 and save its empty result as empty.json. Then send your CCCC peer two request_reply messages in immediate succession in one shell call, with distinct operation IDs. Ask the peer to reply to the first using the exact text 'ash $FIRST_TOKEN' and to the second using the exact text 'pine $SECOND_TOKEN'. Wait for both replies with chat peek --min-messages 2 --wait-seconds 10, with an overall limit of 210 seconds. The response batches are arrays of message arrays. Use jq '[.batches[][]] | length' to count both messages and save the populated peek as peek.json. In the same shell call, use chat pop --snapshot SNAPSHOT --operation-id OPERATION with its exact snapshot and a fresh operation ID before the snapshot expires. Save the output as pop.json, run chat ack --receipt RECEIPT using pop.json's receipt and save ack.json, then run chat pop-result --operation-id OPERATION with the same operation ID and save result.json. In this same turn, run jq -r '.batches[][] | .handle' on pop.json and use chat reply with each handle, writing 'confirmed' followed by that message's full text. After sending the confirmations, create ready-to-release in queue-$TOKEN. Wait in a shell for the operator to create release in that directory, for at most 150 seconds, then finish this turn." \
  > "$CASE_EVIDENCE/b-active-prompt.json" &
B_ACTIVE_PID=$!
lab wait-execution --role b --mode busy --timeout 60 > "$CASE_EVIDENCE/b-active-busy.json"
for ((attempt=0; attempt<300; attempt++)); do
  if [[ -f "$QUEUE_PROOF_DIR/ready-to-release" ]]; then
    break
  fi
  sleep 1
done
test -f "$QUEUE_PROOF_DIR/ready-to-release"
cp "$QUEUE_PROOF_DIR/"{empty,peek,pop,ack,result}.json "$CASE_EVIDENCE/"
```

While B is still busy, ask A to send a new request. Confirm that the provider offered it and that its marker is absent from B's transcript before releasing the active turn.

```bash
next_request() {
  lab prompt --role a \
    --prompt "Use the houmao-cccc executable selected by cccc-brief.json and send one CCCC request_reply asking your peer to reply with $NEXT_TOKEN. Finish after storing the request."
}
lab wait-execution --role a --mode ready --require-open --timeout 60 > "$CASE_EVIDENCE/a-next-ready.json"
if ! next_request > "$CASE_EVIDENCE/a-next-request.json" 2> "$CASE_EVIDENCE/a-next-request.stderr"; then
  rg -Fq 'The owner has an unresolved prompt attempt.' "$CASE_EVIDENCE/a-next-request.stderr"
  lab scan --role a --token "$NEXT_TOKEN" --expect absent > "$CASE_EVIDENCE/a-next-retry-check.json"
  lab wait-execution --role a --mode ready --require-open --timeout 30 > "$CASE_EVIDENCE/a-next-retry-ready.json"
  next_request > "$CASE_EVIDENCE/a-next-request.json"
fi
for ((attempt=0; attempt<20; attempt++)); do
  if lab verify --token "$NEXT_TOKEN" --allow-no-reply --expected-attempts offered --timeout 3 \
    > "$CASE_EVIDENCE/next-staged.json" 2> "$CASE_EVIDENCE/next-staged.stderr"; then
    break
  fi
  sleep 1
done
jq -e '.chronological_attempt_states == ["offered"]' "$CASE_EVIDENCE/next-staged.json" >/dev/null
lab wait-execution --role b --mode busy --timeout 10 > "$CASE_EVIDENCE/b-before-release.json"
lab scan --role b --token "$NEXT_TOKEN" --expect absent > "$CASE_EVIDENCE/next-native-absent.json"
touch "$QUEUE_PROOF_DIR/release"
wait "$B_ACTIVE_PID"
lab verify --token "$NEXT_TOKEN" --expected-attempts accepted > "$CASE_EVIDENCE/next-round-trip.json"
lab verify-batch --tokens "$NEXT_TOKEN" > "$CASE_EVIDENCE/next-native-request.json"
lab wait-execution --role b --mode ready --require-open --timeout 90 > "$CASE_EVIDENCE/b-final-ready.json"
```

## Verify Exact Reads and Reply Parents

Preserve both transcripts and the channel audit. Use the provider's event and attempt records to confirm that B read precisely the two peer replies and answered both original parents. Check that the follow-up used the same attempt before and after readiness.

```bash
for role in a b; do
  lab transcript --role "$role" --output "$CASE_EVIDENCE" > "$CASE_EVIDENCE/$role-transcripts.json"
done
lab audit > "$CASE_EVIDENCE/channel-audit.json"
pixi run python "$BUNDLE_ROOT/helpers/verify_queue_access.py" \
  --run-meta "$RUN_META" --evidence "$CASE_EVIDENCE" --first "$FIRST_TOKEN" --second "$SECOND_TOKEN" \
  > "$CASE_EVIDENCE/queue-proof.json"
```

The proof requires one native prompt and an accepted attempt for the yielded request. B must have successful peek, pop, acknowledgment, result lookup, and reply calls in one native turn. Each popped message must have one `gateway_tool_read` attempt, an exact-parent confirmation, and no ordinary CCCC prompt on B. The follow-up must move from `offered` to `accepted` on the same attempt after B yields. Keep the evidence through the bundle cleanup.
