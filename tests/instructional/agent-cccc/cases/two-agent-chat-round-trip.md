# Two Agents Complete Work Through CCCC Chat

Two Houmao-managed agents discover one another in a run-owned CCCC Group. One asks the other to read a local file and answer through `request_reply`; the recipient performs the file read and authors a threaded CCCC chat reply without using any mail channel.

## Sub-cases

- `t1-attachment-preserves-body`: plugin attachment preserves both native body PIDs, supervisor identities, and native conversation IDs.
- `t2-peer-discovery-and-request`: the sender uses its local binding and Group membership to send one `request_reply` event to the peer Actor.
- `t3-agent-authored-work-and-reply`: the recipient reads the requested file and sends one native `send` reply with the original event as its parent.
- `t4-no-mail-fallback`: neither agent invokes filesystem mail, online mail, CCCC Mail, or provider administration.

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
  --prompt "Read cccc-brief.json in your workspace. Use only CCCC chat to ask the peer to read shared-note.txt in its workspace and reply with the file's single-word contents plus the marker $TOKEN. Use request_reply. Inspect the handoff receipt, then finish without waiting for the reply." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

- **Wait for and verify the native round trip.** The helper reads CCCC history and delivery receipts. It requires one request, one threaded reply containing `cobalt`, `request_reply` followed by native `send`, and exactly one accepted handoff:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --reply-contains cobalt \
  --expected-attempts accepted --timeout 300 \
  > "$CASE_EVIDENCE/round-trip.json"
```

- **Capture both transcripts.** Run `transcript --role a` and `transcript --role b` with `--output "$CASE_EVIDENCE"`. Save the sender's `chat history --limit 100` and the request's `chat deliveries --event-ref EVENT_REF` output as `history.json` and `deliveries.json`; obtain `EVENT_REF` from `round-trip.json` with `jq -r '.request.event_ref'`.
- **Audit actual tool calls.** Run `cccc_lab.py audit --run-meta "$RUN_META" > "$CASE_EVIDENCE/channel-audit.json"`. It must report no Houmao mail, CCCC Mail, or CCCC provider-admin calls. The transcripts must also show the sender's member discovery and chat send, and the recipient's file read and chat reply.
- **Proof.** Keep `doctor.json`, `a-prompt.json`, `round-trip.json`, `history.json`, `deliveries.json`, both transcripts, and `channel-audit.json` under `CASE_EVIDENCE` and confirm they remain after cleanup.

## Gotchas

- A stored CCCC event does not prove handoff or completed work. Require the accepted delivery attempt and the recipient's transcript.
- Do not prompt the recipient directly to read or answer; its incoming CCCC offer must trigger that behavior.
- The sender can finish before the recipient answers. Wait on native CCCC history rather than assuming turn ordering.
- If either agent uses a mailbox or CCCC provider administration, record the channel-audit failure; do not remove those commands from the evidence.

## Blinding and Transcript Checks

- Keep evaluation vocabulary out of operator prompts and agent-facing filenames. `TOKEN` is a neutral work identifier, not a grading instruction.
- Grade from native DSH tool calls, the file-reading side effect in the transcript, CCCC history, and delivery receipts, not from either agent's final summary.
- Both agents use the general correspondent role; neither receives an acknowledgement-only role or an exact send/reply command in the operator prompt.
