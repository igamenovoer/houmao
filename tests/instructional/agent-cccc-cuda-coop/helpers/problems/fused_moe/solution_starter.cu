#include "kernel_api.cuh"

#include <cmath>
#include <cfloat>

namespace moe {
namespace {

__device__ __forceinline__ float silu_f32(float z) {
    return z / (1.0f + expf(-z));
}

// Starter unfused per-token kernels (intentionally unoptimized):
// Processes each token independently without grouping by expert, so every token
// streams full [I, H] and [H, I] expert weights from global memory.
__global__ void moe_router_top2_kernel(
    const float* __restrict__ x,
    const float* __restrict__ router_w,
    int32_t* __restrict__ top_experts,
    float* __restrict__ top_weights,
    int32_t num_tokens) {
    const int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= num_tokens) {
        return;
    }
    const float* x_row = x + static_cast<size_t>(t) * kHiddenDim;

    float best0 = -FLT_MAX;
    float best1 = -FLT_MAX;
    int e0 = 0;
    int e1 = 1;

    for (int e = 0; e < kNumExperts; ++e) {
        const float* rw = router_w + static_cast<size_t>(e) * kHiddenDim;
        float acc = 0.0f;
        for (int h = 0; h < kHiddenDim; ++h) {
            acc += x_row[h] * rw[h];
        }
        if (acc > best0) {
            best1 = best0;
            e1 = e0;
            best0 = acc;
            e0 = e;
        } else if (acc > best1) {
            best1 = acc;
            e1 = e;
        }
    }

    const float m = fmaxf(best0, best1);
    const float p0 = expf(best0 - m);
    const float p1 = expf(best1 - m);
    const float inv = 1.0f / (p0 + p1);
    top_experts[t * 2 + 0] = e0;
    top_experts[t * 2 + 1] = e1;
    top_weights[t * 2 + 0] = p0 * inv;
    top_weights[t * 2 + 1] = p1 * inv;
}

__global__ void moe_up_swiglu_kernel(
    const float* __restrict__ x,
    const float* __restrict__ w_gate,
    const float* __restrict__ w_up,
    const int32_t* __restrict__ top_experts,
    float* __restrict__ act_buf,
    int32_t num_tokens) {
    const int slot = blockIdx.x;
    const int j = blockIdx.y * blockDim.x + threadIdx.x;
    if (slot >= num_tokens * kTopK || j >= kInterDim) {
        return;
    }
    const int t = slot / kTopK;
    const int e = top_experts[slot];

    const float* x_row = x + static_cast<size_t>(t) * kHiddenDim;
    const size_t w_offset = (static_cast<size_t>(e) * kInterDim + j) * kHiddenDim;
    const float* wg = w_gate + w_offset;
    const float* wu = w_up + w_offset;

    float g_acc = 0.0f;
    float u_acc = 0.0f;
    for (int h = 0; h < kHiddenDim; ++h) {
        const float xv = x_row[h];
        g_acc += xv * wg[h];
        u_acc += xv * wu[h];
    }
    act_buf[static_cast<size_t>(slot) * kInterDim + j] = silu_f32(g_acc) * u_acc;
}

__global__ void moe_down_combine_kernel(
    const float* __restrict__ act_buf,
    const float* __restrict__ w_down,
    const int32_t* __restrict__ top_experts,
    const float* __restrict__ top_weights,
    float* __restrict__ y,
    int32_t num_tokens) {
    const int t = blockIdx.x;
    const int h = blockIdx.y * blockDim.x + threadIdx.x;
    if (t >= num_tokens || h >= kHiddenDim) {
        return;
    }

    float out = 0.0f;
    for (int r = 0; r < kTopK; ++r) {
        const int slot = t * kTopK + r;
        const int e = top_experts[slot];
        const float w = top_weights[slot];
        const float* a_row = act_buf + static_cast<size_t>(slot) * kInterDim;
        const float* wd = w_down + (static_cast<size_t>(e) * kHiddenDim + h) * kInterDim;
        float acc = 0.0f;
        for (int j = 0; j < kInterDim; ++j) {
            acc += a_row[j] * wd[j];
        }
        out += w * acc;
    }
    y[static_cast<size_t>(t) * kHiddenDim + h] = out;
}

struct StarterWorkspace {
    int32_t* top_experts = nullptr;
    float* top_weights = nullptr;
    float* act_buf = nullptr;
    int32_t capacity_tokens = 0;

    void ensure(int32_t num_tokens) {
        if (num_tokens <= capacity_tokens) {
            return;
        }
        cudaFree(top_experts);
        cudaFree(top_weights);
        cudaFree(act_buf);
        cudaMalloc(&top_experts, static_cast<size_t>(num_tokens) * kTopK * sizeof(int32_t));
        cudaMalloc(&top_weights, static_cast<size_t>(num_tokens) * kTopK * sizeof(float));
        cudaMalloc(&act_buf, static_cast<size_t>(num_tokens) * kTopK * kInterDim * sizeof(float));
        capacity_tokens = num_tokens;
    }
};

StarterWorkspace& get_workspace() {
    static StarterWorkspace ws;
    return ws;
}

}  // namespace

void launch_fused_moe_custom(const FusedMoeArgs& args) {
    if (args.num_tokens <= 0) {
        return;
    }
    auto& ws = get_workspace();
    ws.ensure(args.num_tokens);

    const int router_threads = 128;
    const int router_blocks = (args.num_tokens + router_threads - 1) / router_threads;
    moe_router_top2_kernel<<<router_blocks, router_threads, 0, args.stream>>>(
        args.x, args.router_w, ws.top_experts, ws.top_weights, args.num_tokens);

    dim3 up_grid(static_cast<unsigned int>(args.num_tokens * kTopK),
                 static_cast<unsigned int>((kInterDim + 127) / 128));
    moe_up_swiglu_kernel<<<up_grid, 128, 0, args.stream>>>(
        args.x, args.w_gate, args.w_up, ws.top_experts, ws.act_buf, args.num_tokens);

    dim3 down_grid(static_cast<unsigned int>(args.num_tokens),
                   static_cast<unsigned int>((kHiddenDim + 127) / 128));
    moe_down_combine_kernel<<<down_grid, 128, 0, args.stream>>>(
        ws.act_buf, args.w_down, ws.top_experts, ws.top_weights, args.y, args.num_tokens);
}

}  // namespace moe
