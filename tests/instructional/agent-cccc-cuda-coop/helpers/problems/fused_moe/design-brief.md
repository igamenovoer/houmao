# Fused Top-K MoE SwiGLU Block Optimization Brief

## Goal

Optimize `moe::launch_fused_moe_custom` in `solution.cu` so it matches the exact double-precision reference across arbitrary token counts and skewed expert distributions while maximizing end-to-end composed GPU throughput.

## Mathematical Specification

Constants in `kernel_api.cuh`:
- `kNumExperts = 16`, `kTopK = 2`, `kHiddenDim = 512`, `kInterDim = 1024`.

For each token `t in [0, num_tokens)`:
1. Compute router logits `logits[e] = dot(x[t, :], router_w[e, :])` for `e in [0, 16)`.
2. Select top-2 experts `(e0, e1)` with highest `logits[e]` (tie-break: smaller expert index wins).
3. Compute renormalized softmax weights over the top-2 logits:
   - `m = max(logits[e0], logits[e1])`
   - `w0 = exp(logits[e0] - m) / (exp(logits[e0] - m) + exp(logits[e1] - m))`, `w1 = 1 - w0`.
4. For each selected `(e_r, w_r)` (`r in {0, 1}`):
   - `gate = x[t, :] @ w_gate[e_r]^T` (shape `[1024]`)
   - `up   = x[t, :] @ w_up[e_r]^T` (shape `[1024]`)
   - `act  = silu(gate) * up` where `silu(z) = z / (1 + exp(-z))`
   - `out_r = act @ w_down[e_r]^T` (shape `[512]`)
5. Combine outputs: `y[t, :] = w0 * out_0 + w1 * out_1`.

## Constraints & Workflow

- Edit **only** `solution.cu`. Do not modify `driver.cu`, `kernel_api.cuh`, or `Makefile`.
- Keep all dependencies within standard C++17 and the CUDA Toolkit (`nvcc`, `ncu`, `nsys`).
- Do not mutate any `const` input buffer and do not hardcode `num_tokens` or router skew patterns (note that some experts can receive 0 tokens on small or skewed batches).
- Accuracy requirement: `|got - ref| <= 1e-3 + 1e-3 * |ref|` on `y`.
- Useful commands in this workspace:
  - `make run` — compile, verify accuracy and input immutability, and time against the naive baseline.
  - `make profile-ncu` — collect SM/DRAM throughput, occupancy, and register pressure via `ncu`.
  - `make profile-nsys` — inspect kernel launch timeline via `nsys`.
