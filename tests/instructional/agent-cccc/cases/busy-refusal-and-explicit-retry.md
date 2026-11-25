# A Busy Peer Causes One Explicit CCCC Retry

A real recipient turn occupies Agent B while Agent A sends a `request_reply` chat. CCCC stores the request and records a refused handoff without replaying it. After B becomes ready, A explicitly retries the original event and B answers it; no duplicate request or mailbox fallback is allowed.

## Sub-cases

- `t1-real-busy-refusal`: B's native execution is running when A's request arrives, and the first delivery attempt is `refused`.
- `t2-idle-does-not-replay`: B's transcript still lacks the request token after it becomes ready.
- `t3-sender-explicit-retry`: A uses `chat retry` on the original event, producing a second, accepted attempt for the same native request.
- `t4-threaded-result`: B performs the requested response and A observes exactly one request and one threaded reply.

## How to get to it (user POV)

- The same healthy pair from the round-trip case is idle and `doctor` exits zero.
- The operator gives B an ordinary long-running shell task, waits for real busy state, and then asks A to contact B.
- Once B is ready, the operator asks A to reconcile the refused event through CCCC rather than sending a new request.

## Driving it with cccc_lab

Preconditions:

- Set `CASE_EVIDENCE="$EVIDENCE/busy-refusal-and-explicit-retry"`, create it, and choose a fresh neutral `TOKEN`.
- Run Doctor into `$CASE_EVIDENCE/doctor.json` before the first drive and after any failed drive.

- **Occupy B through a real prompt.** Launch this synchronous prompt in the background so the harness can inspect the busy state:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role b \
  --prompt "Use a shell tool to run sleep 45, then reply with the single word rested." \
  > "$CASE_EVIDENCE/b-busy-prompt.json" 2> "$CASE_EVIDENCE/b-busy-prompt.stderr" &
BUSY_PROMPT_PID=$!
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode busy --timeout 60 \
  > "$CASE_EVIDENCE/b-busy.json"
```

- **Send while B is busy.** Ask A to send a `request_reply` request containing `TOKEN`, inspect the receipt, and stop without retrying:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace. Use only CCCC chat to ask the peer to reply with the marker $TOKEN. Use request_reply. Inspect the handoff receipt, then finish without waiting or retrying." \
  > "$CASE_EVIDENCE/a-initial-prompt.json"
```

- **Verify only the refused attempt.** Run:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --allow-no-reply \
  --expected-attempts refused --timeout 60 \
  > "$CASE_EVIDENCE/refused.json"
```

- **Wait for B to finish the unrelated turn.** Wait for the background prompt, require readiness, and confirm that no delayed offer reached B:

```bash
wait "$BUSY_PROMPT_PID"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode ready --timeout 90 \
  > "$CASE_EVIDENCE/b-ready.json"
sleep 3
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/no-replay-before-retry.json"
```

- **Ask A for an explicit retry.** The prompt states the reconciliation intent without supplying a command:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Read cccc-brief.json in your workspace. Find the earlier CCCC request containing $TOKEN and inspect its history and deliveries. The peer is ready now. Explicitly retry that original event to the same peer with chat retry. Do not create another send or use a mailbox. Finish after the retry is accepted." \
  > "$CASE_EVIDENCE/a-retry-prompt.json"
```

- **Verify the complete chain.** Run the following command, then capture both transcripts, native history, deliveries, and `channel-audit.json` as in the round-trip case:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --reply-contains "$TOKEN" \
  --expected-attempts refused,accepted --timeout 300 \
  > "$CASE_EVIDENCE/round-trip.json"
```
- **Proof.** Require busy-state evidence, the refused receipt, absence from B's transcript before retry, the sender transcript showing `chat retry`, exactly `refused,accepted` attempts, one threaded reply, and a clean channel audit.

## Gotchas

- Do not simulate busyness by editing internal state or holding a gateway lock. B must be executing an ordinary operator turn.
- Do not use `chat send` for the retry. The native request ID must remain unchanged and only the delivery-attempt list may grow.
- If the initial handoff is `failed` or `uncertain` rather than `refused`, record the actual state and classify the setup; do not relabel it as busy refusal.
- A reply received before the explicit retry invalidates the no-replay assertion.

## Blinding and Transcript Checks

- Use neutral work prompts and tokens; do not tell either agent how its behavior will be graded.
- The initial and retry prompts state the operator's delivery intent but do not supply exact CCCC commands.
- Grade refusal, retry, and response from native delivery receipts and both transcripts. Agent claims about readiness or sending are insufficient.
