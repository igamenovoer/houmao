# Two Agents Complete Work Through CCCC Chat

Two Houmao-managed agents discover one another in a run-owned CCCC Group. One asks the other to read a local file and answer through `request_reply`; the recipient performs the file read and authors a threaded CCCC chat reply without using any mail channel.

## Sub-cases

- `t1-attachment-preserves-body`: plugin attachment preserves both native body PIDs, supervisor identities, and native conversation IDs.
- `t2-peer-discovery-and-request`: the sender uses its local binding and Group membership to send one `request_reply` event to the peer Actor.
- `t3-agent-authored-work-and-reply`: the recipient reads the requested file and sends one native `send` reply with the original event as its parent.
- `t4-no-mail-fallback`: neither agent invokes filesystem mail, online mail, CCCC Mail, or provider administration.
- `t5-handoff-inspection-by-handle`: the sender uses the short handle returned by send, and the recipient uses the handle in the request fence. Both receipts report the native request and the same handoff attempt.

## How to get to it (user POV)

- Both agents launched through the supported fixture have seeded native conversations and healthy gateways; `configure` attaches distinct CCCC Actors without replacing either body.
- `doctor` exits zero and the operator has a neutral token in `TOKEN`.
- The operator asks the sender in natural language to obtain a file-reading result from the peer through CCCC chat.

## Driving it with cccc_lab

Preconditions:

- `RUN_META`, `EVIDENCE`, `TOKEN`, and `CASE_EVIDENCE="$EVIDENCE/two-agent-chat-round-trip"` are set; create `CASE_EVIDENCE`.
- Both workdirs contain `shared-note.txt` with the single word `cobalt` written by the harness as an ordinary work fixture.
- Run `cccc_lab.py doctor --run-meta "$RUN_META"` and save the result as `$CASE_EVIDENCE/doctor.json` before this drive.

- **Ask the sender to delegate the work.** Use an ordinary operator request, not a prepared CLI command:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace and use the houmao-cccc executable it selects. Send one CCCC request_reply asking the peer to read shared-note.txt and reply with the file's single-word contents plus the marker $TOKEN. Ask the peer to use the executable from its own cccc-brief.json to inspect the request's handoff by the short handle in the incoming request. It should save that receipt JSON as cccc-deliveries.json in its workspace before replying. Save your send JSON as cccc-send.json, inspect the handoff by its short message handle, and save your own receipt JSON as cccc-deliveries.json. Finish without waiting for the reply." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

- **Wait for and verify the native round trip.** The helper reads CCCC history and delivery receipts. It requires one request, one threaded reply containing `cobalt`, `request_reply` followed by native `send`, and exactly one accepted handoff:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --reply-contains cobalt \
  --expected-attempts accepted --timeout 300 \
  > "$CASE_EVIDENCE/round-trip.json"
```

- **Prove the compact request fence.** Use the batch verifier to capture the compact single-message fence and its handle:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN" \
  > "$CASE_EVIDENCE/native-request.json"
```

- **Capture both transcripts.** Run `transcript --role a` and `transcript --role b` with `--output "$CASE_EVIDENCE"`. Save the sender's `chat history --limit 100` and the request's `chat deliveries --event-ref EVENT_REF` output as `history.json` and `deliveries.json`; obtain `EVENT_REF` from `round-trip.json` with `jq -r '.request.event_ref'`.
- **Audit actual tool calls.** Run `cccc_lab.py audit --run-meta "$RUN_META" > "$CASE_EVIDENCE/channel-audit.json"`. It must report no Houmao mail, CCCC Mail, or CCCC provider-admin calls. The transcripts must also show the sender's member discovery and chat send, and the recipient's file read and chat reply.
- **Compare the agents' receipts with the independent lookup.** After both agents have completed the requested commands, save their receipt outputs and compare the original event and attempt IDs. Receipt states can differ if one lookup ran before the handoff was settled.

```bash
cp "$RUN_A/workdir/cccc-send.json" "$CASE_EVIDENCE/a-send.json"
cp "$RUN_A/workdir/cccc-deliveries.json" "$CASE_EVIDENCE/a-handle-deliveries.json"
cp "$RUN_B/workdir/cccc-deliveries.json" "$CASE_EVIDENCE/b-handle-deliveries.json"
jq -e -s 'map({event_id, attempts: [.deliveries[].attempt_id]}) | length == 3 and (.[0].event_id | type == "string") and (.[0].attempts | length == 1 and (.[0] | type == "string")) and (unique | length == 1)' \
  "$CASE_EVIDENCE/deliveries.json" "$CASE_EVIDENCE/a-handle-deliveries.json" \
  "$CASE_EVIDENCE/b-handle-deliveries.json" > "$CASE_EVIDENCE/receipt-identity-match.json"
```

- **Proof.** Require `round-trip.json` to pass with chronological attempt states `["accepted"]`, and `native-request.json` to show one fenced entry with a `msg_` handle and no binding or event reference. In the native tool calls, verify both agents used the `houmao-cccc` executable selected for the run. A calls `chat deliveries --handle` with the handle from `a-send.json`. B calls it with the handle from `native-request.json`, reads the file, and replies through that handle. The channel audit must pass. Keep the caller outputs and both transcripts under `CASE_EVIDENCE` and confirm they remain after cleanup.

## Gotchas

- A stored CCCC event does not prove handoff or completed work. Require the accepted delivery attempt and the recipient's transcript.
- Do not prompt the recipient directly to read or answer; its incoming CCCC offer must trigger that behavior.
- The sender can finish before the recipient answers. Wait on native CCCC history rather than assuming turn ordering.
- If either agent uses a mailbox or CCCC provider administration, record the channel-audit failure; do not remove those commands from the evidence.

## Blinding and Transcript Checks

- Keep evaluation vocabulary out of operator prompts and agent-facing filenames. `TOKEN` is a neutral work identifier, not a grading instruction.
- Grade from native DSH tool calls, the file-reading side effect in the transcript, CCCC history, and delivery receipts, not from either agent's final summary.
- Both agents use the general correspondent role; neither receives an acknowledgement-only role or an exact send/reply command in the operator prompt.
