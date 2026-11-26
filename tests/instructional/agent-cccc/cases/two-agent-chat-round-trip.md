# Two Agents Complete Work Through CCCC Chat

Two Houmao-managed agents discover one another in a run-owned CCCC Group. One asks the other to read a local file and answer through `request_reply`; the recipient performs the file read and authors a threaded reply by handle without using any mail channel.

## Sub-cases

- `t1-attachment-preserves-body`: plugin attachment preserves both native body PIDs, supervisor identities, and native conversation IDs.
- `t2-pull-transport-active`: the recipient's effective delivery transport is `pull` for this scenario.
- `t3-peer-discovery-and-request`: the sender discovers the peer and sends one `request_reply` using a current connection token and operation ID.
- `t4-handle-authored-work-and-reply`: the recipient reads the file and sends one native `send` reply to the exact incoming handle and original parent.
- `t5-compact-request-fence`: the native request contains one ordered message entry with sender, timestamp, mode, body, and handle, without the binding ID or signed event reference.
- `t6-no-mail-fallback`: neither agent invokes filesystem mail, online mail, CCCC Mail, or provider administration.
- `t7-handoff-inspection-by-handle`: the sender uses the short handle returned by send, and the recipient uses the handle in the request fence. Both receipts report the native request and the same handoff attempt.

## How to get to it (user POV)

- Both agents launched through the supported fixture have seeded native conversations and healthy gateways; `configure` attaches distinct CCCC Actors without replacing either body.
- The operator selects pull delivery for the recipient, `doctor` exits zero, and a fresh neutral token is set.
- The operator asks the sender in natural language to obtain a file-reading result from the peer through CCCC chat.

## Driving it with cccc_lab

Preconditions:

- `RUN_META`, `EVIDENCE`, and `TOKEN` are set; create `CASE_EVIDENCE="$EVIDENCE/two-agent-chat-round-trip"`.
- Both workdirs contain `shared-note.txt` with the single word `cobalt`.
- Run Doctor before this drive:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
```

- **Pin pull delivery.** Select pull on the recipient and require an active effective setting:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy pull \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Ask the sender to delegate the work.** Use an ordinary operator request, not a prepared CLI command:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace and use the houmao-cccc executable it selects. Send one CCCC request_reply asking the peer to read shared-note.txt and reply with the file's single-word contents plus the marker $TOKEN. Ask the peer to use the executable from its own cccc-brief.json to inspect the request's handoff by the short handle in the incoming request. It should save that receipt JSON as cccc-deliveries.json in its workspace before replying. Save your send JSON as cccc-send.json, inspect the handoff by its short message handle, and save your own receipt JSON as cccc-deliveries.json. Finish without waiting for the reply." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

- **Verify the native round trip.** The helper requires one `request_reply`, one replied `send`, a `cobalt` reply, and exactly one accepted handoff:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --reply-contains cobalt \
  --expected-attempts accepted --timeout 300 \
  > "$CASE_EVIDENCE/round-trip.json"
```

- **Prove the compact request fence.** The batch verifier accepts a one-message fence and rejects leaked binding, event, handle-reuse, and duplicate-URL data:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN" \
  > "$CASE_EVIDENCE/native-request.json"
```

- **Capture both transcripts and provider views.** Save history, the request's deliveries, both native transcripts, and the channel audit:

```bash
EVENT_REF="$(jq -r '.request.event_ref' "$CASE_EVIDENCE/round-trip.json")"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" cccc \
  --run-meta "$RUN_META" --role a chat history --limit 100 \
  > "$CASE_EVIDENCE/history.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" cccc \
  --run-meta "$RUN_META" --role a chat deliveries --event-ref "$EVENT_REF" --limit 100 \
  > "$CASE_EVIDENCE/deliveries.json"
for ROLE in a b; do
  pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" transcript \
    --run-meta "$RUN_META" --role "$ROLE" --output "$CASE_EVIDENCE" \
    > "$CASE_EVIDENCE/$ROLE-transcripts.json"
done
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" audit \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/channel-audit.json"
```

- **Compare the agents' receipts with the independent lookup.** After both agents have completed the requested commands, save their receipt outputs and compare the original event and attempt IDs. Receipt states can differ if one lookup ran before the handoff was settled.

```bash
cp "$RUN_A/workdir/cccc-send.json" "$CASE_EVIDENCE/a-send.json"
cp "$RUN_A/workdir/cccc-deliveries.json" "$CASE_EVIDENCE/a-handle-deliveries.json"
cp "$RUN_B/workdir/cccc-deliveries.json" "$CASE_EVIDENCE/b-handle-deliveries.json"
jq -e -s 'map({event_id, attempts: [.deliveries[].attempt_id]}) | length == 3 and (.[0].event_id | type == "string") and (.[0].attempts | length == 1 and (.[0] | type == "string")) and (unique | length == 1)' \
  "$CASE_EVIDENCE/deliveries.json" "$CASE_EVIDENCE/a-handle-deliveries.json" \
  "$CASE_EVIDENCE/b-handle-deliveries.json" > "$CASE_EVIDENCE/receipt-identity-match.json"
```

- **Proof.** Require `delivery.json` to show effective pull, `round-trip.json` to pass with chronological attempt states `["accepted"]`, and `native-request.json` to show one fenced entry with a `msg_` handle and no binding or event reference. In the native tool calls, verify both agents used the `houmao-cccc` executable selected for the run and passed the brief's Group ID to `members --group` successfully. A calls `chat deliveries --handle` with the handle from `a-send.json`. B calls it with the handle from `native-request.json`, reads the file, and replies through that handle. The channel audit must pass. Keep the caller outputs and both transcripts under `CASE_EVIDENCE` and confirm they remain after cleanup.

## Gotchas

- Set pull explicitly. A previous scenario can leave the shared run on a push policy.
- Message handles expire after connection changes. Use the handle from the current native request, not an old handle.
- An optional ordinary acknowledgement from the sender is not a second request. Only `request_reply` events are counted as the request under test.
- Do not prompt the recipient directly to read or answer; its incoming CCCC request must trigger that behavior.
- The sender can finish before the recipient answers. Wait on native CCCC history and delivery receipts rather than turn ordering.
- A stored CCCC event does not prove handoff or completed work. Require the accepted attempt, B's transcript, and the threaded reply.
- If either agent uses a mailbox or CCCC provider administration, preserve the channel-audit failure.

## Blinding and Transcript Checks

- Keep evaluation vocabulary out of operator prompts and agent-facing filenames. `TOKEN` is a neutral work identifier.
- Grade from native tool calls, the file-reading side effect, CCCC history, the compact request fence, and delivery receipts. Use the agent summaries only for context.
- Both agents use the general correspondent role; neither receives an acknowledgement-only role or an exact send/reply command in the operator prompt.
