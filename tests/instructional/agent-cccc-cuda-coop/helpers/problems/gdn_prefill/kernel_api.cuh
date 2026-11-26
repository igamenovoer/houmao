#pragma once

#include <cuda_runtime.h>
#include <cstdint>

namespace gdn {

constexpr int kNumQKHeads = 4;
constexpr int kNumVHeads = 8;
constexpr int kHeadDim = 128;
constexpr int kGvaGroup = kNumVHeads / kNumQKHeads;  // 2

struct GdnPrefillArgs {
    const float* q;           // [total_tokens, kNumQKHeads, kHeadDim]
    const float* k;           // [total_tokens, kNumQKHeads, kHeadDim]
    const float* v;           // [total_tokens, kNumVHeads, kHeadDim]
    const float* init_state;  // [num_seqs, kNumVHeads, kHeadDim, kHeadDim] or nullptr (k-last: [V, K])
    const float* a_log;       // [kNumVHeads]
    const float* a;           // [total_tokens, kNumVHeads]
    const float* dt_bias;     // [kNumVHeads]
    const float* b;           // [total_tokens, kNumVHeads]
    const int32_t* cu_seqlens;  // [num_seqs + 1], device pointer
    float* output;            // [total_tokens, kNumVHeads, kHeadDim]
    float* new_state;         // [num_seqs, kNumVHeads, kHeadDim, kHeadDim] (k-last: [V, K])
    int32_t num_seqs;
    int32_t total_tokens;
    float scale;              // if <= 0.0f, use 1.0f / sqrtf(kHeadDim)
    cudaStream_t stream;
};

// Implemented in solution.cu. Must not modify any const input buffers.
void launch_gdn_prefill_custom(const GdnPrefillArgs& args);

// Naive baseline provided by driver.cu for direct comparison.
void launch_gdn_prefill_baseline(const GdnPrefillArgs& args);

}  // namespace gdn
