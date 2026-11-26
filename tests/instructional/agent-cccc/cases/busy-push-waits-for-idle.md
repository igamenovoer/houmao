# Push ASAP Waits for a Busy Recipient

Agent B runs a real operator turn while Agent A sends a CCCC `request_reply` message. CCCC retains the pending work. Agent B receives one compact request after becoming idle and replies to its original parent.

## Sub-cases

- `t1-asap-policy-active`: the recipient's effective delivery setting is `push` with `push_policy=asap`.
- `t2-busy-before-send`: B is executing a real native shell turn before A's request is stored.
- `t3-no-busy-admission`: the request token is absent from B's native transcript while B remains busy.
- `t4-delivery-after-idle`: the pending request enters B's transcript only after the busy turn ends.
- `t5-exact-threaded-reply`: CCCC records one accepted handoff and B replies to the original parent by handle.
- `t6-no-mail-fallback`: neither agent invokes a mailbox or CCCC provider administration.

## How to get to it (user POV)

- Both agents are healthy and attached to the same CCCC Group.
- The operator starts a real long-running turn on Agent B, waits until B is observably busy, and then asks Agent A to send through CCCC.
- The operator watches B remain without the request while busy, receive it after becoming idle, and answer it.

## Driving it with cccc_lab

Preconditions:

- `RUN_META`, `EVIDENCE`, and `TOKEN` are set; create `CASE_EVIDENCE="$EVIDENCE/busy-push-waits-for-idle"`.
- Both agents are idle before B's busy turn starts.
- Run Doctor and select ASAP delivery before the busy turn:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy asap \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Occupy B through a real prompt.** Launch the synchronous prompt in the background so the harness can inspect the live busy state:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role b \
  --prompt 'Run sleep 60 using a shell tool, then end this turn.' \
  > "$CASE_EVIDENCE/b-busy-prompt.json" &
BUSY_PROMPT_PID=$!
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode busy --timeout 60 \
  > "$CASE_EVIDENCE/b-busy.json"
```

- **Send while B is busy.** Ask A to store one request and finish:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Ask your peer through CCCC request_reply to return the marker $TOKEN. Finish after storing the message." \
  > "$CASE_EVIDENCE/a-prompt.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/not-admitted-while-busy.json"
```

- **Wait for the busy turn and verify the delayed delivery.** Require B to become ready before checking the accepted handoff:

```bash
wait "$BUSY_PROMPT_PID"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode ready --timeout 90 \
  > "$CASE_EVIDENCE/b-ready.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --expected-attempts accepted \
  > "$CASE_EVIDENCE/round-trip.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect present \
  > "$CASE_EVIDENCE/delivered-after-idle.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN" \
  > "$CASE_EVIDENCE/native-request.json"
```

- **Capture both transcripts and provider views.** Save history, request deliveries, both native transcripts, and the channel audit:

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

- **Proof.** Require effective ASAP delivery, `not-admitted-while-busy.json` to report zero occurrences, `round-trip.json` to show one request, one accepted attempt, and exact reply ancestry, and `delivered-after-idle.json` to report the token present after readiness. `native-request.json` must show one compact fenced request with a current handle. A's transcript must contain exactly one request send carrying the token; an optional ordinary acknowledgement is not a duplicate request. Keep every artifact under `CASE_EVIDENCE` and confirm it remains after cleanup.

## Gotchas

- The send must land while B is genuinely busy. If B finishes before A stores the request, repeat with a longer B turn and a fresh token.
- Do not simulate busyness by editing internal state, holding a gateway lock, or sending raw terminal input.
- CCCC may record only one immutable `accepted` attempt when admission waits before the native handoff. Do not expect a synthetic deferred or refused state unless readiness changed after dispatch started.
- A pending delivery is not a completed reply. Wait for B's readiness, the accepted receipt, and the exact-parent response.
- A handle is valid only for the current connection. Do not reuse an old handle after a reconnect or policy transition.
- Preserve failed or uncertain receipts as observed; do not weaken the expected state list to force a pass.

## Blinding and Transcript Checks

- Use neutral work prompts and a fresh marker; do not tell either agent how the delay will be graded.
- Grade the absence during busy time and the later presence from B's actual native transcript, then grade the handoff and reply from CCCC receipts and ancestry.
- The operator prompt states the delivery intent but does not supply exact CCCC command lines.
