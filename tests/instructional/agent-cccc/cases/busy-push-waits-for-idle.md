# Push ASAP Waits for a Busy Recipient

Agent B runs a real operator turn while Agent A sends a CCCC `request_reply` message. CCCC retains the pending work. Agent B receives one request after becoming idle and replies to its original parent.

## Drive

Run Doctor and select a fresh neutral `TOKEN`. Use a distinct `CASE_EVIDENCE="$EVIDENCE/busy-push-waits-for-idle"` directory. Set B to push ASAP and wait for the effective policy.

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" delivery \
  --run-meta "$RUN_META" --role b --policy asap > "$CASE_EVIDENCE/delivery.json"

pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role b \
  --prompt 'Run sleep 45 using a shell tool, then end this turn.' \
  > "$CASE_EVIDENCE/b-busy-prompt.json" &
BUSY_PROMPT_PID=$!
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode busy > "$CASE_EVIDENCE/b-busy.json"

pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Ask your peer through CCCC request_reply to return the marker $TOKEN. Finish after storing the message." \
  > "$CASE_EVIDENCE/a-prompt.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/not-admitted-while-busy.json"

wait "$BUSY_PROMPT_PID"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --expected-attempts accepted \
  > "$CASE_EVIDENCE/round-trip.json"
```

## Evidence

Capture both transcripts, provider history and deliveries, and the channel audit. Require one native request prompt after B's busy turn ends, one accepted attempt, and one exact threaded reply. The sender's native transcript must contain one send. Run the case again with a longer B turn if A takes too long to send while B is busy.
