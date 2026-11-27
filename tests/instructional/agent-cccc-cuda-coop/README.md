# CCCC Chat During Five Minutes of CUDA Optimization

Status: draft

Can four Houmao-managed Web agents use CCCC chat reliably while they work on a kernel? The tester gives four Qwen 3.8 peers the same task, observes any discussion they initiate, and traces attempted messages to the intended native sessions. The first naturally delivered message is the first evidence that the path works. The run continues for the full five minutes to expose later failures and deliveries while a peer is busy.

## Case Index

| Case | Workload | Decision |
| --- | --- | --- |
| [GDN prefill](cases/four-agent-cuda-coop.md) | Manifest default, five verification shapes | Which directed routes carried the peers’ chat, and what happened to each attempted send? |
| [Fused MoE](cases/manifest-problem-switch.md) | Explicit `--problem fused_moe`, four verification shapes | Does the same setup carry naturally occurring chat during a different optimization problem? |

Start each case with a fresh group and four fresh sessions. Record the two results individually. Each run samples up to 12 directed routes. Limit conclusions to the workload, observed routes, and five-minute window.

## Baseline and Isolation

Use the Houmao checkout, Pixi, Bash, `jq`, `curl`, tmux, `make`, a CUDA compiler, and a GPU visible to `nvidia-smi`. Run one case at a time on that GPU. `ncu` and `nsys` are available to peers when installed. The independent verifier uses `nvcc`.

Select one external DSH or Kimi Web model-pool entry for `Qwen/Qwen3.8-27B-FP8` with `HOUMAO_TEST_MODEL`. All four launches use that entry’s client, routing, reasoning settings, and tool configuration. Set `CCCC_ENDPOINT` to a running receiver-v2 CCCC service with timed push delivery. The tester also samples queue state when the provider advertises that capability. Use matching workspace builds of `houmao-mgr` and `houmao-cccc`. Keep credentials outside the checkout. [Fixture guide](../../../scripts/agents/test-fixtures/README.md) · [Plugin setup](../../../packages/houmao-cccc/README.md)

Each peer starts in its own physical `workdir` with its own `solution.cu`, brief, locked driver, header, Makefile, and build products. “Private” is a working convention. The four sessions run as the same OS user and can access each other’s files. CCCC chat is the team discussion channel. Each peer may research, implement, measure, or speak whenever it chooses. CCCC may display its first actor as `foreman` in membership metadata. All four receive the same assignment and authority in this experiment.

## Launch

From the checkout root, use one Bash shell for the case. Leave `PROBLEM_ID` unset for GDN. Set `PROBLEM_ID=fused_moe` for MoE. A run-private link under `tmp/instructional-tests/` points to the neutral runtime path. Launch prepares the four idle sessions before releasing any task.

```bash
set -euo pipefail
umask 077
unset TMUX TMUX_PANE TMUX_TMPDIR
: "${CCCC_ENDPOINT:?Set the CCCC receiver endpoint}"
: "${HOUMAO_TEST_MODEL:?Select the external Qwen Web pool key}"
unset HOUMAO_TEST_MODEL_PEER_A HOUMAO_TEST_MODEL_PEER_B HOUMAO_TEST_MODEL_PEER_C HOUMAO_TEST_MODEL_PEER_D
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"
BUNDLE_ROOT="$REPO_ROOT/tests/instructional/agent-cccc-cuda-coop"
FIXTURE="$REPO_ROOT/scripts/agents/test-fixtures/fixture.py"
LAB="$BUNDLE_ROOT/helpers/cuda_coop_lab.py"
case "${PROBLEM_ID:-gdn_prefill}" in
  gdn_prefill) CASE=four-agent-cuda-coop; problem_args=() ;;
  fused_moe) CASE=manifest-problem-switch; problem_args=(--problem fused_moe) ;;
  *) exit 2 ;;
esac
export HOUMAO_MGR="${HOUMAO_MGR:-$REPO_ROOT/.pixi/envs/default/bin/houmao-mgr}"
export HOUMAO_CCCC="${HOUMAO_CCCC:-$REPO_ROOT/.pixi/envs/default/bin/houmao-cccc}"
CCCC_PRIVATE_ROOT="${CCCC_PRIVATE_ROOT:-$HOME/.local/state/houmao/cccc-instructional}"
service_args=()
if [[ -n "${CCCC_SERVICE_RUNTIME:-}" || -n "${CCCC_PROVIDER_BINARY:-}" ]]; then
  service_args=(--service-runtime "${CCCC_SERVICE_RUNTIME:?Set the local runtime receipt}"
                --provider-binary "${CCCC_PROVIDER_BINARY:?Set the matching binary}")
fi
pixi install
test -x "$HOUMAO_MGR"
test -x "$HOUMAO_CCCC"
curl -fsS "$CCCC_ENDPOINT/api/v1/health" >/dev/null
mkdir -p "$REPO_ROOT/tmp/cuda-coop" "$REPO_ROOT/tmp/instructional-tests"
RUN_TMP=$(mktemp -d "$REPO_ROOT/tmp/cuda-coop/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX")
RUN_ID=${RUN_TMP##*/}
RUN_LINK="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
git check-ignore -q "$RUN_TMP"
git check-ignore -q "$RUN_LINK"
ln -sT "$RUN_TMP" "$RUN_LINK"
EVIDENCE="$RUN_TMP/evidence/agent-cccc-cuda-coop/$CASE"
RUN_META="$RUN_TMP/run-meta.json"
mkdir -p "$EVIDENCE" "$RUN_TMP/runtime" "$RUN_TMP/scripts"
peers=(peer-a peer-b peer-c peer-d)
cleanup() {
  if [[ -s "$RUN_META" ]]; then
    pixi run python "$LAB" stop --run-meta "$RUN_META" > "$EVIDENCE/stop.json"
  else
    for peer in "${peers[@]}"; do
      if [[ -s "$EVIDENCE/$peer-prepare.json" ]]; then
        dir=$(jq -er '.run_dir' "$EVIDENCE/$peer-prepare.json")
        pixi run python "$FIXTURE" stop --run-dir "$dir" > "$EVIDENCE/$peer-stop.json" || continue
      fi
    done
  fi
}
trap cleanup EXIT
pixi run python "$LAB" show-manifest "${problem_args[@]}" > "$EVIDENCE/manifest-resolved.json"
model=$(jq -er '.team_model' "$EVIDENCE/manifest-resolved.json")
pixi run python "$FIXTURE" check --pool-key "$HOUMAO_TEST_MODEL" --mode web --surface manager --live > "$EVIDENCE/pool-check.json"
jq -e --arg model "$model" '.configuration.model == $model' "$EVIDENCE/pool-check.json" >/dev/null
for peer in "${peers[@]}"; do
  prompt="$RUN_TMP/runtime/$peer.md"
  { cat "$BUNDLE_ROOT/helpers/prompts/common.md"; echo; cat "$BUNDLE_ROOT/helpers/prompts/$peer.md"; } > "$prompt"
  pixi run python "$FIXTURE" prepare --pool-slot "$peer" --mode web --surface manager \
    --prompt-mode unattended --tmux-server new --role "$peer" --system-prompt-file "$prompt" \
    --run-root "$RUN_TMP/runtime/$peer" > "$EVIDENCE/$peer-prepare.json"
  dir=$(jq -er '.run_dir' "$EVIDENCE/$peer-prepare.json")
  pixi run python "$FIXTURE" launch --run-dir "$dir" > "$EVIDENCE/$peer-launch.json"
done
pixi run python "$LAB" configure "${problem_args[@]}" --endpoint "$CCCC_ENDPOINT" \
  --private-root "$CCCC_PRIVATE_ROOT" "${service_args[@]}" \
  --run-meta "$RUN_META" --evidence-root "$EVIDENCE" > "$EVIDENCE/configure.json"
```

## Doctor

```bash
pixi run python "$LAB" doctor --run-meta "$RUN_META" > "$EVIDENCE/doctor.json" 2> "$EVIDENCE/doctor.stderr"
pixi run python "$LAB" delivery --run-meta "$RUN_META" --policy batch --quiet-interval 6 --max-wait 15 > "$EVIDENCE/delivery.json"
```

Require four distinct managed sessions, actor identities, bindings, and workdirs in one fresh group. Doctor checks the group roster at every gateway, model selection, readiness, native body identity across attachment, GPU, and seeded files. Confirm that the batch policy became active on all four bindings. The six- and fifteen-second settings govern batching. They impose no speaking schedule or end-to-end latency requirement.

## Drive

```bash
window_exit=0
pixi run python "$LAB" run-window --run-meta "$RUN_META" > "$EVIDENCE/window.json" 2> "$EVIDENCE/window.stderr" || window_exit=$?
collection_exit=0
pixi run python "$LAB" collect --run-meta "$RUN_META" > "$EVIDENCE/collect.json" 2> "$EVIDENCE/collect.stderr" || collection_exit=$?
```

`run-window` saves initial journal offsets, file hashes, queue state, and empty group history. It submits the same kernel assignment with the same absolute deadline to all four peers concurrently. The five minutes start at dispatch. Inspect each native journal for the identical kickoff and report any dispatch skew. During the window the tester observes gateway health, bindings, and queues using read-only calls. Let the clock run through silence, idle periods, and active work. The tester sends zero follow-ups and performs zero queue pops or acknowledgments.

At 300 seconds the helper records journal end offsets and freezes the available source files, then requests an interrupt on each run-owned session. It records capture times and rejects source files that changed after the deadline. `collect` copies the bounded native journal excerpts and reads each actor’s paginated history and each sender’s delivery receipts before teardown. Filter by the release and cutoff timestamps. A receipt retrieved later may describe later work. Record an uncertain boundary when native append times or pre-cutoff journal offsets cannot establish which side of the deadline a record belongs to. The timestamp inside the CCCC fence identifies the original send. For a post-cutoff binding check, keep the observation time and the interrupt time distinct.

## Evidence

Store raw evidence in `$EVIDENCE`, accessible through the operator link. Keep it owner-private. Operator views may contain scoped handles and native tool arguments. Cite redacted identifiers or file and row references in the report.

| Question | Evidence |
| --- | --- |
| Did four peers get a fair start? | `manifest-resolved.json`, `pool-check.json`, four prepare and launch receipts, `configure.json`, `doctor.json`, `delivery.json`, `window/baseline.json`, `window/history-before.json`, `window/release.json`, `window/kickoffs.json`, and the four native kickoff rows |
| What did the tester observe? | `window/*-observations.jsonl` records host timestamps, status, binding identity, and available non-consuming queue snapshots. Each sample also records journal byte offsets, which can confirm that a row existed before cutoff. Compare each actor’s final read-only `window/communication/<peer>/binding-after.json` to its initial binding before teardown. Inspect any gaps, disconnects, and changes in binding or session identity. |
| What happened to each attempted send? | Sender tool call and result, `window/communication/<peer>/history.json`, `deliveries-*.json` in the sender’s evidence, and the recipient’s native journal excerpt under `window/communication/<peer>/runtime/homes/`. `window/collection.json` lists capture errors. |
| What was available at the deadline? | `window/timer.json`, `window/cutoff.json`, `window/cutoff/<peer>/`, and `window/interrupts.json`. Capture times bound any uncertainty at the deadline. |
| Which CUDA implementations worked? | `window/cuda-results.json` maps peers to source hashes and locked-file mismatches. Under `window/cuda/<sha256>/`, `independent-verify.json` records the clean build and driver result, including workload timings. `solution-diff.patch` shows the change from the starter. |

### Grading Communication

Start with actual send and reply attempts in the four sender journals, including errors before an event was stored. Merge copies of a stored event by `event_id`. For each intended recipient, record the sender, operation or event ID, destination, send time, receipt attempts and states, native journal location, and observed delivery time. Resolve recipients from the actual send/reply addressing and group membership. Visibility in a history query alone cannot establish delivery.

Match each receipt to a native CCCC input fence or a successful consuming **peer** tool result using the actor, sender, timestamp, mode, and text. Confirm reply linkage when present. Count a logical message once per intended recipient. Distinguish receipt retries from duplicate native deliveries. Check the other journals for misroutes, including in multi-recipient sends. Count user-input errors, service rejections, accepted events, confirmed recipients, late or still-pending deliveries, missing evidence, wrong recipients, and unexplained duplicates separately. Record the delay where timestamps support it and whether the recipient appeared busy. If a peer reads content through history or a non-consuming peek, record that the message was visible to that peer. Count it separately from a gateway handoff or a consuming read. Re-reading history creates no duplicate handoff.

Report confirmed and attempted directed routes out of 12. For a communication `PASS`, require at least one independently confirmed in-window peer delivery, all valid in-scope attempts accounted for, exactly one intact native handoff per intended recipient within the window, and zero evidenced unintended deliveries or channel outages. Unsent routes remain unexercised. A pending send near the cutoff or a gap in capture can leave delivery unverified. A confirmed service rejection of a valid send, wrong recipient, corrupted payload, unexplained duplicate, outage, or loss warrants `FAIL` with its evidence. When the evidence establishes no such failure, an executed run with insufficient traffic or unresolved evidence receives `FAIL (insufficient evidence)` under the case verdict convention. Attribute a transport defect only when a valid attempt or observed outage and its independent evidence establish the failure. Report malformed peer commands as agent usability findings. Kernel correctness, speedup, how many peers spoke, and adherence to a personality have no weight in the communication verdict.

## Cleanup

Collect communication evidence before deleting the group. Stop only this run’s four sessions and private sockets. Verify each distinct frozen source once on the idle GPU against the authoritative driver and header. If an agent survives cleanup, resolve its recorded run-owned process before timing kernels.

```bash
trap - EXIT
cleanup_exit=0
cleanup || cleanup_exit=$?
cuda_exit=0
if (( cleanup_exit == 0 )) && [[ -s "$EVIDENCE/window/cutoff.json" ]]; then
  pixi run python "$LAB" verify-cuda --run-meta "$RUN_META" --verify-dir "$RUN_TMP/runtime/verify" \
  > "$EVIDENCE/verify.json" 2> "$EVIDENCE/verify.stderr" || cuda_exit=$?
else
  cuda_exit=125
fi
jq -n --argjson w "$window_exit" --argjson c "$collection_exit" --argjson s "$cleanup_exit" --argjson v "$cuda_exit" '{window:$w,collection:$c,cleanup:$s,cuda:$v}' > "$EVIDENCE/exit-codes.json"
find "$EVIDENCE" -type f ! -name evidence-check.txt | sort > "$EVIDENCE/evidence-check.txt"
```

Inspect `stop.json` for all four stop receipts, run-owned tmux cleanup, grant revocations, group absence, and credential removal. Record any residue and its exact owner. Keep the evidence, run metadata, and all cited artifacts. Runtime builds can be discarded after verification. On an interrupted or partial launch, the exit trap uses the metadata or the individual fixture receipts to clean up. Preserve the failed step’s diagnostics and assign `BLOCKED` if setup prevented a valid drive. Use `VERIFIED-UNREACHABLE` for a demonstrated unavailable external prerequisite.

### Run Report

After cleanup, write a redacted Markdown report to the operator’s explicit destination, otherwise under `IMSIGHT_SKILL_OUTPUT_DIR` if set (relative paths resolve from the checkout root). The default is `$REPO_ROOT/.imsight-arts/project-mgr/agent-driven-testing/reports/$RUN_ID.md`. Include checkout and tool versions, model and pool key, group and window, attempted sends, recipient-level outcomes, route coverage, timing uncertainty, and one communication verdict for the case. Cite one concrete end-to-end trace or the first failed checkpoint. Record CUDA results, interference, cleanup, and usability issues separately. Both cases remain draft until a live report supports promotion.

## Helpers

`pixi run python "$LAB" --help` lists the manifest, setup, observation, verification, and teardown commands invoked above. The common system prompt supplies CCCC usage. The four private additions describe research preferences. The CUDA fixtures and problem selection live alongside the harness. [Prompts](helpers/prompts/) · [CUDA fixtures](helpers/problems/) · [Manifest](manifest.toml)
