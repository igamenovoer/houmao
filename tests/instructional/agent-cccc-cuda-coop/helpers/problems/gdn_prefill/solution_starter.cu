#include "kernel_api.cuh"

#include <cmath>

namespace gdn {
namespace {

__device__ __forceinline__ float stable_softplus(float x) {
    return (x > 20.0f) ? x : log1pf(expf(x));
}

__device__ __forceinline__ float sigmoid_f32(float x) {
    return 1.0f / (1.0f + expf(-x));
}

// Starter sequential recurrence kernel (intentionally unoptimized):
// One block per (seq, v_head), 128 threads over V dimension; keeps state in global memory
// and streams the entire [D, D] matrix twice per token.
__global__ void gdn_prefill_starter_kernel(
    const float* __restrict__ q,
    const float* __restrict__ k,
    const float* __restrict__ v,
    const float* __restrict__ init_state,
    const float* __restrict__ a_log,
    const float* __restrict__ a,
    const float* __restrict__ dt_bias,
    const float* __restrict__ b,
    const int32_t* __restrict__ cu_seqlens,
    float* __restrict__ output,
    float* __restrict__ new_state,
    float scale) {
    const int seq = blockIdx.x;
    const int hv = blockIdx.y;
    const int v_idx = threadIdx.x;
    if (v_idx >= kHeadDim) {
        return;
    }

    const int hqk = hv / kGvaGroup;
    const int seq_start = cu_seqlens[seq];
    const int seq_end = cu_seqlens[seq + 1];

    const size_t state_base =
        (static_cast<size_t>(seq) * kNumVHeads + hv) * kHeadDim * kHeadDim;
    float* s_row = new_state + state_base + static_cast<size_t>(v_idx) * kHeadDim;

    if (init_state != nullptr) {
        const float* init_row = init_state + state_base + static_cast<size_t>(v_idx) * kHeadDim;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_row[ki] = init_row[ki];
        }
    } else {
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_row[ki] = 0.0f;
        }
    }

    const float exp_a_log = expf(a_log[hv]);
    const float bias = dt_bias[hv];

    for (int t = seq_start; t < seq_end; ++t) {
        const float a_val = a[static_cast<size_t>(t) * kNumVHeads + hv];
        const float b_val = b[static_cast<size_t>(t) * kNumVHeads + hv];
        const float g = expf(-exp_a_log * stable_softplus(a_val + bias));
        const float beta = sigmoid_f32(b_val);

        const float* k_ptr = k + (static_cast<size_t>(t) * kNumQKHeads + hqk) * kHeadDim;
        const float* q_ptr = q + (static_cast<size_t>(t) * kNumQKHeads + hqk) * kHeadDim;
        const float v_val = v[(static_cast<size_t>(t) * kNumVHeads + hv) * kHeadDim + v_idx];

        float pred = 0.0f;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            const float s_old = g * s_row[ki];
            s_row[ki] = s_old;
            pred += s_old * k_ptr[ki];
        }

        const float delta = beta * (v_val - pred);
        float out_acc = 0.0f;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            const float s_new = s_row[ki] + delta * k_ptr[ki];
            s_row[ki] = s_new;
            out_acc += s_new * q_ptr[ki];
        }

        output[(static_cast<size_t>(t) * kNumVHeads + hv) * kHeadDim + v_idx] = scale * out_acc;
    }
}

}  // namespace

void launch_gdn_prefill_custom(const GdnPrefillArgs& args) {
    if (args.num_seqs <= 0) {
        return;
    }
    const float scale = (args.scale > 0.0f) ? args.scale : (1.0f / sqrtf(static_cast<float>(kHeadDim)));
    dim3 grid(static_cast<unsigned int>(args.num_seqs), static_cast<unsigned int>(kNumVHeads));
    dim3 block(static_cast<unsigned int>(kHeadDim));
    gdn_prefill_starter_kernel<<<grid, block, 0, args.stream>>>(
        args.q,
        args.k,
        args.v,
        args.init_state,
        args.a_log,
        args.a,
        args.dt_bias,
        args.b,
        args.cu_seqlens,
        args.output,
        args.new_state,
        scale);
}

}  // namespace gdn
