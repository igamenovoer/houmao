# Gated Delta Net (GDN) Prefill Optimization Brief

## Goal

Optimize `gdn::launch_gdn_prefill_custom` in `solution.cu` so it matches the exact double-precision reference across arbitrary variable-length batches (`cu_seqlens`, including empty or unaligned sequence lengths and optional non-null `init_state`) while maximizing throughput on the local NVIDIA GPU.

## Mathematical Specification

Constants in `kernel_api.cuh`:
- `kNumQKHeads = 4`, `kNumVHeads = 8` (GVA mapping `hqk = hv / 2`), `kHeadDim = 128`.
- State layout is k-last: `[num_seqs, kNumVHeads, V=128, K=128]`.

For each sequence `s in [0, num_seqs)` and value head `hv in [0, 8)` (`hqk = hv / 2`):
1. Initialize `S[V, K]` to `init_state[s, hv, :, :]` if `init_state != nullptr`, otherwise zeros.
2. For each token `t` from `cu_seqlens[s]` to `cu_seqlens[s + 1] - 1`:
   - `g_t = exp(-exp(a_log[hv]) * softplus(a[t, hv] + dt_bias[hv]))`
   - `beta_t = sigmoid(b[t, hv])`
   - `S_old = g_t * S`
   - `pred_v = S_old @ k_t` (shape `[V]`)
   - `delta_v = beta_t * (v_t - pred_v)`
   - `S = S_old + outer(delta_v, k_t)`
   - `output[t, hv, :] = scale * (S @ q_t)` (where `scale = 1 / sqrt(128)` when `args.scale <= 0`)
3. Store final `S` into `new_state[s, hv, :, :]` (even when `cu_seqlens[s] == cu_seqlens[s + 1]`, preserving `init_state` or zeros).

## Constraints & Workflow

- Develop the implementation in your private `solution.cu`. Keep the supplied driver, header, and Makefile intact. Publish the chosen team implementation to `team/solution.cu` before the deadline.
- Keep all dependencies within standard C++17 and the CUDA Toolkit (`nvcc`, `ncu`, `nsys`).
- Do not mutate any `const` input buffer and do not hardcode sequence lengths or batch sizes.
- Accuracy requirement: `|got - ref| <= 1e-3 + 1e-3 * |ref|` on both `output` and `new_state`.
- Useful commands in this workspace:
  - `make run` — compile, verify accuracy and input immutability, and time against the naive baseline.
  - `make run-all` checks every scored workload and prints JSON. Compare the geometric mean of the per-shape `custom_ms` values.
  - `make profile-ncu` — collect SM/DRAM throughput, occupancy, and register pressure via `ncu`.
  - `make profile-nsys` — inspect kernel launch timeline via `nsys`.
