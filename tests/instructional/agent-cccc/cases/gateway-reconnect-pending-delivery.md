# Gateway Reconnect Delivers Pending Work

Agent B's gateway detaches while its body remains alive. A new CCCC message waits at the provider. Reattaching the same plugin selection lets B claim and handle the pending work.

## Drive

Run Doctor and select a fresh neutral `TOKEN`. Use a distinct `CASE_EVIDENCE="$EVIDENCE/gateway-reconnect-pending-delivery"` directory.

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" detach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-detach.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Ask your peer through CCCC request_reply to return the marker $TOKEN. Finish after storing the message." \
  > "$CASE_EVIDENCE/a-prompt.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --allow-no-reply --expected-attempts pending \
  > "$CASE_EVIDENCE/pending.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" scan \
  --run-meta "$RUN_META" --role b --token "$TOKEN" --expect absent \
  > "$CASE_EVIDENCE/not-delivered-while-detached.json"

pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" attach \
  --run-meta "$RUN_META" --role b > "$CASE_EVIDENCE/b-attach.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" verify \
  --run-meta "$RUN_META" --token "$TOKEN" --expected-attempts accepted \
  > "$CASE_EVIDENCE/round-trip.json"
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role a --mode ready
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" wait-execution \
  --run-meta "$RUN_META" --role b --mode ready
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
```

## Evidence

Capture both transcripts, provider history and deliveries, and the channel audit. Require the same native body and CCCC binding before and after reattachment, one pending request while detached, one accepted handoff after reattachment, and one exact threaded reply. Inspect the original attempt identity across both observations.
