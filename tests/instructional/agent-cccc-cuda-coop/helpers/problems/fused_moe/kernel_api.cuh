#pragma once

#include <cuda_runtime.h>
#include <cstdint>

namespace moe {

constexpr int kNumExperts = 16;
constexpr int kTopK = 2;
constexpr int kHiddenDim = 512;
constexpr int kInterDim = 1024;

struct FusedMoeArgs {
    const float* x;         // [num_tokens, kHiddenDim]
    const float* router_w;  // [kNumExperts, kHiddenDim]
    const float* w_gate;    // [kNumExperts, kInterDim, kHiddenDim]
    const float* w_up;      // [kNumExperts, kInterDim, kHiddenDim]
    const float* w_down;    // [kNumExperts, kHiddenDim, kInterDim]
    float* y;               // [num_tokens, kHiddenDim]
    int32_t num_tokens;
    cudaStream_t stream;
};

// Implemented in solution.cu. Must not modify any const input buffers.
void launch_fused_moe_custom(const FusedMoeArgs& args);

// Naive baseline provided by driver.cu for direct comparison.
void launch_fused_moe_baseline(const FusedMoeArgs& args);

}  // namespace moe
