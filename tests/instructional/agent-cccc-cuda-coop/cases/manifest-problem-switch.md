# Manifest Problem Selection Switches Four-Agent Workflow to Fused MoE

Selecting Problem 2 (`fused_moe`, Fused Top-K MoE SwiGLU block) via `manifest.toml` (through `--problem fused_moe` or changing `default_problem`) provisions a clean four-agent CCCC workspace with the MoE specification, starter unfused baseline, and locked verification driver, then executes the full four-agent collaborative optimization loop without modifying the harness.

## Sub-cases

- `t1-manifest-problem-override`: `show-manifest --problem fused_moe` and `configure --problem fused_moe` resolve `fused_moe` from `manifest.toml` and seed the MoE problem files (`design-brief.md`, `kernel_api.cuh`, `driver.cu`, `solution.cu`, `Makefile`).
- `t2-four-agent-moe-collaboration`: all four agents (`lead`, `algo`, `kernel`, `profiler`) coordinate over CCCC chat to profile the unfused per-token baseline, design expert grouping / tiled SwiGLU fusion, implement `solution.cu`, and verify improvements.
- `t3-independent-moe-extended-verification`: compiling ONLY `solution.cu` against the untouched locked MoE `driver.cu` with `-DEXTENDED_SHAPES=1` passes balanced, skewed, odd-tail (`T=37` with zero-token experts), and heavy-skew (`T=1536`) shapes while preserving input immutability and beating the baseline.
- `t4-no-mail-or-admin-fallback`: channel audit confirms zero peer mail or provider-admin tool calls across all four agents.

## How to get to it (user POV)

- The operator sets `export PROBLEM_ID=fused_moe` (or updates `default_problem = "fused_moe"` in a run-local copy of `manifest.toml`), runs `Launch` and `configure --problem fused_moe`, confirms `doctor` exits zero, and sends one organic task kickoff prompt to `lead`.
- After the four-agent discussion settles, the operator runs `verify-cuda` and `audit` to independently check the submitted MoE kernel and CCCC transcripts.

## Driving it with cuda_coop_lab

Preconditions:

- Initialize a fresh run via [README.md](../README.md) with `PROBLEM_ID=fused_moe` and a managed Web pool entry selected for each role. The `configure` command seeds `helpers/problems/fused_moe/` into `$WORKSPACE_DIR`.
- Create `CASE_EVIDENCE="$EVIDENCE/manifest-problem-switch"` and `VERIFY_DIR="$RUN_TMP/runtime/independent-verify-moe"`.
- Run Doctor before driving:

```bash
mkdir -p "$CASE_EVIDENCE"
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" show-manifest \
  --manifest "$MANIFEST" --problem fused_moe > "$CASE_EVIDENCE/manifest-selected.json"
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" doctor \
  --run-meta "$RUN_META" > "$CASE_EVIDENCE/doctor.json"
```

Confirm that Doctor records all four `agents.<role>.pool_slot` values and that each `pool_key` matches the corresponding `$EVIDENCE` preflight (`<role>-check.json`).

- **Pin timed push-batch delivery across all four agents:**

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" delivery \
  --run-meta "$RUN_META" --role all --policy batch --quiet-interval 6 --max-wait 15 \
  > "$CASE_EVIDENCE/delivery.json"
```

- **Kick off the MoE optimization task with `lead`:**

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" prompt \
  --run-meta "$RUN_META" --role lead --timeout 600 \
  --prompt "Read cccc-brief.json in your workspace and design-brief.md in $WORKSPACE_DIR. Coordinate our four-person CUDA team (lead, algo, kernel, profiler) over CCCC chat to optimize the MoE block in $WORKSPACE_DIR/solution.cu. Have profiler establish baseline timing and ncu bottlenecks first, algo design the routing/permutation and grouped tiled MLP fusion strategy (handling skewed and empty experts safely), kernel implement solution.cu without touching driver.cu, kernel_api.cuh, or Makefile, and profiler verify accuracy and speedup on make run plus ncu metrics (targeting at least 3x speedup over the starter baseline). Keep all coordination in CCCC chat and summarize the verified result when ready." \
  > "$CASE_EVIDENCE/lead-kickoff.json"
```

- **Wait for quiescence across all four agents:**

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" wait-idle \
  --run-meta "$RUN_META" --timeout 900 --quiesce-seconds 15 \
  > "$CASE_EVIDENCE/quiesce.json"
```

- **Run independent locked-driver verification (solo GPU) and full audit:**

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" verify-cuda \
  --run-meta "$RUN_META" --verify-dir "$VERIFY_DIR" \
  --evidence-dir "$CASE_EVIDENCE" --run-ncu \
  > "$CASE_EVIDENCE/verify-cuda-stdout.json"
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" audit \
  --run-meta "$RUN_META" --evidence-dir "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/audit-summary.json"
```

- **Proof.** Retain `manifest-selected.json`, `doctor.json`, `delivery.json`, `lead-kickoff.json`, `quiesce.json`, `submitted-solution.cu`, `solution-diff.patch`, `independent-verify.json`, `ncu-summary.txt`, `cccc-history.json`, `participation-summary.json`, `channel-audit.json`, and all four `transcript-*.jsonl` files under `$CASE_EVIDENCE` after cleanup.

## Expected Outcome (Soft Goals)

- **Soft goals (runner makes final PASS/FAIL decision):**
  - **Clean manifest-driven problem switching:** Selecting `fused_moe` via `manifest.toml` seamlessly switches seeded files, Doctor checks, and independent verification to the MoE suite with zero harness edits.
  - **Active four-agent collaboration over CCCC:** All four agents meaningfully discuss and execute the MoE optimization pipeline (baseline profiling, expert-grouping/tiling plan, CUDA implementation, re-verification) over CCCC chat.
  - **Verified composed MoE speedup:** The submitted `solution.cu` compiles cleanly against the untouched locked MoE `driver.cu`, passes balanced, skewed, odd-tail (`T=37`), and heavy-skew (`T=1536`) shapes within `rtol=1e-3, atol=1e-3`, preserves input buffers, and delivers a clear verified speedup over the unfused baseline (target $\ge 3\times$, stretch $\ge 10\times$).
- **Observable signals to inspect:** `manifest-selected.json` (`selected_problem == "fused_moe"`), `doctor.json` (`selected_problem == "fused_moe"`), `participation-summary.json`, `cccc-history.json`, `transcript-{lead,algo,kernel,profiler}-*.jsonl`, `solution-diff.patch`, `independent-verify.json`, `ncu-summary.txt`, and `channel-audit.json`.
- **Hard disqualifiers (automatic FAIL):**
  - Any agent uses Houmao mail, online email, CCCC Mail, or provider-admin endpoints.
  - Fewer than all four actors participate in CCCC chat.
  - Independent locked-driver verification fails compilation, fails any visible or extended shape (including empty-expert edge cases on `T=37`), mutates inputs, tampers with locked files, or fails to beat the baseline (`geomean_speedup <= 1.0`).
  - Missing surviving evidence after cleanup or leaked credentials.

## Gotchas

- Start a fresh run (`RUN_ID`, `WORKSPACE_DIR`, `RUN_META`) when switching problems rather than reusing a `gdn_prefill` run directory; each run binds one manifest problem selection in `run-meta.json`.
- Small or heavily skewed batches (`extended_small_odd_37`) routinely leave one or more of the 16 experts with zero assigned tokens—grouped GEMM kernels must guard empty expert ranges cleanly instead of reading out of bounds or dividing by zero.
- Router top-2 tie-breaking picks the smaller expert index when logits are identical; keep FP32 accumulation consistent with the reference router.

## Blinding and Transcript Checks

- Agent-visible files and kickoff prompts avoid evaluation meta-words (`eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, `arena`).
- Grade strictly from `independent-verify.json`, `solution-diff.patch`, `cccc-history.json`, `participation-summary.json`, `channel-audit.json`, and all four native transcripts rather than self-reported summaries.
