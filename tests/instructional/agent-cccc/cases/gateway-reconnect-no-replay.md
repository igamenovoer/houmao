# Gateway Reconnect Preserves References Without Replaying Chat

Agent B's gateway detaches while its native body remains alive. Agent A's CCCC request is stored with a failed handoff. Reattaching the same plugin selection preserves B's body, conversation, binding ID, and scoped references, but does not replay the request. A must explicitly retry the original event before B receives and answers it.

## Sub-cases

- `t1-detach-preserves-body`: B's native PID, supervisor identity, and conversation remain unchanged after gateway detach.
- `t2-absent-gateway-fails-handoff`: A stores one request and receives a `failed` delivery attempt.
- `t3-reattach-preserves-binding`: the same plugin selection reconnects with the same binding ID and native body identity.
- `t4-no-automatic-replay`: B's transcript lacks the request after reconnection; A's explicit `chat retry` creates the accepted second attempt and threaded reply.

## How to get to it (user POV)

- The pair is healthy and idle, and both agents already have their CCCC briefs.
- The operator uses normal gateway detach/attach lifecycle commands on B only, then asks A to reconcile the original CCCC event.

## Driving it with cccc_lab

Preconditions:

- Set `CASE_EVIDENCE="$EVIDENCE/gateway-reconnect-no-replay"`, create it, and choose a fresh neutral `TOKEN`.
- Run Doctor into `$CASE_EVIDENCE/doctor.json` before detaching B and again after reattaching it.

- **Detach B and send while its gateway is absent.** The body identity must equal the pre-attachment snapshot. A stops after inspecting the initial receipt:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" detach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-detached.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace. Use only CCCC chat to ask the peer to reply with the marker $TOKEN. Use request_reply. Inspect the handoff receipt, then finish without waiting or retrying." \
  > "$CASE_EVIDENCE/a-initial-prompt.json"
```

- **Verify the failed handoff.** Run:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --allow-no-reply \
  --expected-attempts failed --timeout 60 > "$CASE_EVIDENCE/failed.json"
```

- **Reattach the same selection.** The helper requires the original binding ID and unchanged native body. Run Doctor after reattachment:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" attach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-reattached.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor-after-reattach.json"
```

- **Check for replay and retry explicitly through A.** Only CCCC may carry the request token to B. A must use `chat retry`, not another send:

```bash
sleep 3
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/no-replay-after-reattach.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace. Find the earlier CCCC request containing $TOKEN and inspect its history and deliveries. The peer receiver is connected now. Explicitly retry that original event to the same peer with chat retry. Do not create another send or use a mailbox. Finish after the retry is accepted." \
  > "$CASE_EVIDENCE/a-retry-prompt.json"
```

- **Verify and capture.** Run the following command, then capture both transcripts, history, deliveries, and a clean `channel-audit.json` as in the other cases:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --reply-contains "$TOKEN" \
  --expected-attempts failed,accepted --timeout 300 \
  > "$CASE_EVIDENCE/round-trip.json"
```
- **Proof.** Require the failed attempt, binding/body continuity, no request in B's transcript before explicit retry, exactly `failed,accepted` attempts, one threaded reply, and no forbidden channel calls.

## Gotchas

- Detach B through the recorded manager environment only. Never stop the shared CCCC service or another agent's gateway for this case.
- If reattachment changes the binding ID, stop the scenario and report lost reference continuity instead of driving with the new binding.
- History availability after reconnect does not mean delivery. B must not act on the request until A deliberately retries it or the operator separately requests history inspection.
- If clean detach produces `uncertain` rather than `failed`, preserve the actual receipt and classify the case instead of weakening its expected state.

## Blinding and Transcript Checks

- Keep the request token out of B's operator prompts; only CCCC may deliver it to B.
- Use the transcripts to distinguish an automatic offer from A's later explicit retry.
- Native event ancestry and attempt receipts determine pass/fail, not A's claim that reconnection succeeded.
