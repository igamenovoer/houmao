# Gateway Reconnect Delivers Pending Work

Agent B's gateway detaches while its native body remains alive. A new CCCC request waits at the provider. Reattaching the same plugin selection lets B claim the original pending attempt, receive a fresh scoped handle, and answer the request.

## Sub-cases

- `t1-detach-preserves-body`: detaching B's gateway preserves its native PID, supervisor identity, and native conversation.
- `t2-pending-while-detached`: A's request is stored with one provider attempt in `pending` state and does not enter B's native transcript.
- `t3-reattach-preserves-binding`: the same plugin selection reconnects with the same binding ID and native body.
- `t4-same-attempt-after-reattach`: reattachment changes lease generation but keeps the original attempt and event identity.
- `t5-fresh-handle-delivery`: the recovered fenced request uses a current handle and CCCC records `accepted` on the original attempt.
- `t6-exact-threaded-reply`: B replies to the recovered request's original parent without an explicit sender retry.
- `t7-no-mail-fallback`: neither agent invokes a mailbox or CCCC provider administration.

## How to get to it (user POV)

- Both agents are healthy, idle, and attached to the same CCCC Group.
- The operator detaches only Agent B's gateway, asks Agent A to send through CCCC, and verifies the work waits without entering B's native session.
- The operator reattaches the same plugin selection and watches the original pending request arrive and receive a threaded answer.

## Driving it with cccc_lab

Preconditions:

- `RUN_META`, `EVIDENCE`, and `TOKEN` are set; create `CASE_EVIDENCE="$EVIDENCE/gateway-reconnect-pending-delivery"`.
- Both agents are idle before detachment.
- Run Doctor, then pin ASAP delivery so the recovered request is admitted when B becomes ready:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor-before.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy asap \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Detach B's gateway only.** The helper records current body identity and rejects a binding change later:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" detach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-detach.json"
```

- **Send while B's gateway is absent.** Ask A to store one request and finish:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Ask your peer through CCCC request_reply to return the marker $TOKEN. Finish after storing the message." \
  > "$CASE_EVIDENCE/a-prompt.json"
```

- **Verify pending delivery and native absence.** Do not retry the request:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --allow-no-reply --expected-attempts pending \
  > "$CASE_EVIDENCE/pending.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/not-delivered-while-detached.json"
```

- **Reattach the same selection and verify recovery.** Require the original attempt to become accepted and receive an exact-parent reply:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" attach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-attach.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --expected-attempts accepted \
  > "$CASE_EVIDENCE/round-trip.json"
```

- **Prove one attempt and one body across the transition.** The pending and accepted receipts must name the same event and attempt; the detached and attached body snapshots must match:

```bash
jq -n -e \
  --slurpfile pending "$CASE_EVIDENCE/pending.json" \
  --slurpfile accepted "$CASE_EVIDENCE/round-trip.json" \
  --slurpfile before "$CASE_EVIDENCE/b-detach.json" \
  --slurpfile after "$CASE_EVIDENCE/b-attach.json" '
  ($pending[0].delivery_attempts | length) == 1 and
  ($accepted[0].delivery_attempts | length) == 1 and
  $pending[0].delivery_attempts[0].attempt_id ==
    $accepted[0].delivery_attempts[0].attempt_id and
  $pending[0].delivery_attempts[0].event_id ==
    $accepted[0].delivery_attempts[0].event_id and
  $pending[0].delivery_attempts[0].state == "pending" and
  $accepted[0].delivery_attempts[0].state == "accepted" and
  $accepted[0].native_reply_ancestry == $accepted[0].request.id and
  $before[0].body == $after[0].body
' > "$CASE_EVIDENCE/attempt-continuity.json"
```

- **Prove the recovered request is compact and current.** The fresh handle is valid for the reattached connection, but it need not equal the pre-detachment handle:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify-batch \
  --run-meta "$RUN_META" --tokens "$TOKEN" \
  > "$CASE_EVIDENCE/native-request.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect present \
  > "$CASE_EVIDENCE/delivered-after-reattach.json"
```

- **Finish with readiness and Doctor.** Wait for both agents and preserve the post-reattachment health check:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role a --mode ready > "$CASE_EVIDENCE/a-ready.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode ready > "$CASE_EVIDENCE/b-ready.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor-after.json"
```

- **Capture both transcripts and provider views.** Save history, recovered-request deliveries, both native transcripts, and the channel audit:

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

- **Proof.** Require pending before reattachment, accepted after reattachment, one unchanged event/attempt identity, identical body snapshots, the same binding ID from the helper, a fresh compact request fence with a `msg_` handle, and an exact-parent reply. Do not call `chat retry`; recovery must come from the CCCC pending queue. Keep every artifact under `CASE_EVIDENCE` and confirm it remains after cleanup.

## Gotchas

- Detach only Agent B's gateway through the recorded manager environment. Never stop the shared CCCC service or another agent's gateway.
- Do not use `chat retry`. The scenario specifically proves provider recovery of the original unstarted attempt.
- A pending attempt and an accepted attempt are two observations of one provider attempt, not a chronological two-attempt list. Compare the attempt and event IDs, not array length across time.
- Message handles are connection-scoped and can expire on reattachment. Recovered work mints a fresh handle; the signed internal event reference is not exposed to the model.
- If reattachment changes the binding ID or body identity, stop and report a product regression instead of driving against the replacement.
- If the pending state is `staged` or `uncertain`, preserve and classify the actual receipt rather than relabeling it.
- History availability is not delivery. B must not act until the recovered request is admitted.

## Blinding and Transcript Checks

- Keep the request marker out of B's operator prompts; only CCCC may deliver it to B.
- Grade body continuity, attempt continuity, pending-to-accepted transition, and reply ancestry from the helper artifacts and native transcripts, not from assistant summaries.
- The operator prompt states the delivery intent but does not prescribe exact CCCC command lines.
