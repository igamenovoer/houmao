# Four Agents Optimize Default CUDA Kernel Through CCCC Chat

Four Houmao-managed Web agents (`lead`, `algo`, `kernel`, `profiler`) collaborate exclusively through one run-owned CCCC Group. They optimize the default manifest problem (`gdn_prefill`, Gated Delta Net prefill) using native CUDA tools (`nvcc`, `ncu`, `nsys`). An independent check verifies correctness and speedup against the locked driver.

## Sub-cases

- `t1-manifest-default-resolution`: `manifest.toml` resolves `default_problem = "gdn_prefill"` and auto-detects the local GPU architecture without manual edits.
- `t2-four-agent-group-ready`: each role uses its selected model pool entry. All four agents attach to the same run-unique CCCC Group with preserved native bodies, four distinct Actor IDs, healthy CUDA toolchain, and active timed push-batch delivery.
- `t3-four-way-cccc-discussion`: `lead` discovers `algo`, `kernel`, and `profiler` via `members --group`, broadcasts the engineering task, and all four actors exchange substantive design, implementation, and profiling updates over CCCC chat.
- `t4-cuda-profile-and-iteration`: `profiler` measures baseline latency/`ncu` counters, `algo` proposes a structural/algorithmic optimization, `kernel` edits `solution.cu` and builds with `nvcc`, and `profiler` re-verifies the improved kernel.
- `t5-independent-locked-verification`: compiling ONLY the team's `solution.cu` against the untouched authoritative `driver.cu` with `-DEXTENDED_SHAPES=1` passes all visible and held-out shapes, preserves input immutability, leaves locked workspace files untouched, and beats the naive baseline.
- `t6-no-mail-or-admin-fallback`: none of the four agents invoke Houmao filesystem mail, online email, CCCC Mail, or CCCC provider-admin endpoints.

## How to get to it (user POV)

- The operator selects a pool key for all roles with `HOUMAO_TEST_MODEL`, with optional per-role overrides, then launches four Web agents. They configure the manifest's default problem (`gdn_prefill`) and confirm that `doctor` exits zero.
- The operator sets timed push-batch delivery across all four roles and sends one organic engineering request to `lead` pointing to the shared CUDA workspace.
- After the four-agent discussion settles, the operator runs independent locked CUDA verification and transcript/CCCC auditing.

## Driving it with cuda_coop_lab

Preconditions:

- `Launch` and `configure` from [README.md](../README.md) completed with `PROBLEM_ID` unset (or set to `gdn_prefill`); `RUN_META`, `EVIDENCE`, `WORKSPACE_DIR`, and `RUN_TMP` are exported.
- Create `CASE_EVIDENCE="$EVIDENCE/four-agent-cuda-coop"` and `VERIFY_DIR="$RUN_TMP/runtime/independent-verify-gdn"`.
- Run Doctor before driving:

```bash
mkdir -p "$CASE_EVIDENCE"
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
```

Compare each role's `agents.<role>.pool_key` in `doctor.json` with `pool_key` in that role's `$EVIDENCE` preflight (`<role>-check.json`). Each `pool_slot` in Doctor must match its role.

- **Confirm manifest default.** Record the resolved default manifest without passing `--problem`:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" show-manifest \
  --manifest "$MANIFEST" > "$CASE_EVIDENCE/manifest-default.json"
```

- **Pin timed push-batch delivery across all four agents.** Require active convergence before prompting:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" delivery \
  --run-meta "$RUN_META" --role all --policy batch --quiet-interval 6 --max-wait 15 \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Kick off the optimization task with `lead`.** Send one organic operator prompt with no coaching on exact CCCC flags or low-level solutions:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" prompt \
  --run-meta "$RUN_META" --role lead --timeout 600 \
  --prompt "Read cccc-brief.json in your workspace and design-brief.md in $WORKSPACE_DIR. You are leading our four-person CUDA team (lead, algo, kernel, profiler) over CCCC chat. Coordinate with all three peers to: (1) have profiler measure the starter baseline timing and ncu bottlenecks in $WORKSPACE_DIR, (2) have algo propose a concrete algorithmic and memory-hierarchy optimization plan, (3) have kernel implement the optimized kernel in $WORKSPACE_DIR/solution.cu without modifying driver.cu, kernel_api.cuh, or Makefile, and (4) have profiler verify accuracy and speedup on make run plus updated ncu metrics, iterating if accuracy fails or speedup is still below 3x (aiming for 10x+ if achievable). Keep all team discussion in CCCC chat and finish with a brief summary once the verified solution is ready." \
  > "$CASE_EVIDENCE/lead-kickoff.json"
```

- **Wait for the four-agent discussion to settle.** Wait on observable execution idleness and message quiescence rather than a blind sleep:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" wait-idle \
  --run-meta "$RUN_META" --timeout 900 --quiesce-seconds 15 \
  > "$CASE_EVIDENCE/quiesce.json"
```

- **Run independent locked-driver CUDA verification (solo GPU).** Compile ONLY `$WORKSPACE_DIR/solution.cu` against the untouched authoritative `driver.cu` with `-DEXTENDED_SHAPES=1`, plus capture an `ncu` summary:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" verify-cuda \
  --run-meta "$RUN_META" --verify-dir "$VERIFY_DIR" \
  --evidence-dir "$CASE_EVIDENCE" --run-ncu \
  > "$CASE_EVIDENCE/verify-cuda-stdout.json"
```

- **Cross-check all four transcripts, CCCC history, participation, and channels:**

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" audit \
  --run-meta "$RUN_META" --evidence-dir "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/audit-summary.json"
```

- **Proof.** Retain `manifest-default.json`, `doctor.json`, `delivery.json`, `lead-kickoff.json`, `quiesce.json`, `submitted-solution.cu`, `solution-diff.patch`, `independent-verify.json`, `ncu-summary.txt`, `cccc-history.json`, `participation-summary.json`, `channel-audit.json`, and all four `transcript-*.jsonl` files under `$CASE_EVIDENCE` after cleanup.

## Expected Outcome (Soft Goals)

- **Soft goals (runner makes final PASS/FAIL decision):**
  - **Genuine four-agent technical collaboration over CCCC:** All four agents (`lead`, `algo`, `kernel`, `profiler`) actively participate in the CCCC Group with substantive, domain-grounded messages (baseline measurements, algorithmic/tiling design, implementation handoffs, numerical/profiler feedback) that visibly inform the final `solution.cu`.
  - **Stable four-way CCCC mechanics under real workloads:** Multi-recipient sends, threaded replies, and incoming messages delivered while peers compile or profile settle cleanly without dropping work or wedging any agent.
  - **Meaningful, independently verified CUDA optimization:** The team's `solution.cu` compiles cleanly against the untouched locked `driver.cu`, passes every visible and extended ragged/empty-sequence shape within `rtol=1e-3, atol=1e-3`, preserves read-only inputs, and achieves a clear real speedup over the naive baseline (target $\ge 3\times$ geomean speedup; $\ge 10\times$ stretch when chunkwise WY reformulation is realized).
  - **Clean manifest default behavior:** Running without `--problem` selects `gdn_prefill` from `manifest.toml` automatically.
- **Observable signals to inspect:** `manifest-default.json` (`selected_problem == "gdn_prefill"`), `participation-summary.json` (all 4 actors present, multi-recipient and threaded counts), `cccc-history.json` (actual technical content exchanged), `transcript-{lead,algo,kernel,profiler}-*.jsonl` (real `houmao-cccc`, `nvcc`, `ncu`, and file-edit tool calls), `solution-diff.patch` (real kernel/algorithm changes vs. starter), `independent-verify.json` (`passed == true`, `inputs_immutable == true`, `workspace_locked_files_untouched == true`, `geomean_speedup`), `ncu-summary.txt`, and `channel-audit.json`.
- **Hard disqualifiers (automatic FAIL):**
  - Any agent uses Houmao filesystem mail, online email, CCCC Mail, or CCCC provider-admin endpoints.
  - Fewer than all four actors send messages in `cccc-history.json`, or `solution.cu` is produced by one agent without real peer discussion.
  - Independent verification fails compilation, fails numerical accuracy on any visible or extended shape, mutates read-only inputs, modifies locked workspace files (`driver.cu` or `kernel_api.cuh`), or yields `geomean_speedup <= 1.0`.
  - Any agent crashes/wedges unrecoverably, credentials leak into workspaces or evidence, or required proof artifacts are missing after cleanup.

## Gotchas

- Four concurrent agents sharing an endpoint can take longer to finish a turn, especially with higher reasoning presets. Allow the full `wait-idle` timeout (900s) before declaring a stall.
- `ncu` serializes GPU execution. If `kernel` and `profiler` launch GPU jobs at the same time, in-run timings may fluctuate; always grade final speedup from the runner's solo `verify-cuda` run after `wait-idle`.
- In `gdn_prefill`, empty sequences (`cu_seqlens[s] == cu_seqlens[s+1]`) with non-null `init_state` appear in the extended verification suite—kernels must still copy `init_state` into `new_state` for zero-length slots.
- Watch for usability friction (`usability-issue`) such as agents confusing repeated `--to` flags, stale `--connection-token`, or `chat reply --handle` vs. `chat send` in four-way threads, and report it even on a `PASS`.

## Blinding and Transcript Checks

- Agent-visible filenames (`design-brief.md`, `kernel_api.cuh`, `driver.cu`, `solution.cu`, `Makefile`) and the operator kickoff prompt intentionally avoid evaluation meta-words (`eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, `arena`).
- Grade strictly from `independent-verify.json`, `solution-diff.patch`, `cccc-history.json`, `participation-summary.json`, `channel-audit.json`, and all four native transcripts—never from `lead`'s final summary alone.
- All four roles receive general collaborative CUDA instructions; none are acknowledgement-only stubs or given pre-written CUDA solutions.
