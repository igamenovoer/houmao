#include "kernel_api.cuh"

#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define CUDA_CHECK(call)                                                                   \
    do {                                                                                   \
        cudaError_t err__ = (call);                                                        \
        if (err__ != cudaSuccess) {                                                        \
            fprintf(stderr, "CUDA error %s:%d: %s\n", __FILE__, __LINE__,                  \
                    cudaGetErrorString(err__));                                            \
            std::exit(1);                                                                  \
        }                                                                                  \
    } while (0)

namespace moe {
namespace {

// Authoritative double-precision GPU reference kernels.
__global__ void moe_ref_router_f64_kernel(
    const float* __restrict__ x,
    const float* __restrict__ router_w,
    int32_t* __restrict__ top_experts,
    double* __restrict__ top_weights,
    int32_t num_tokens) {
    const int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= num_tokens) {
        return;
    }
    const float* x_row = x + static_cast<size_t>(t) * kHiddenDim;
    double best0 = -1e300;
    double best1 = -1e300;
    int e0 = 0;
    int e1 = 1;
    for (int e = 0; e < kNumExperts; ++e) {
        const float* rw = router_w + static_cast<size_t>(e) * kHiddenDim;
        double acc = 0.0;
        for (int h = 0; h < kHiddenDim; ++h) {
            acc += static_cast<double>(x_row[h]) * static_cast<double>(rw[h]);
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
    const double m = (best0 > best1) ? best0 : best1;
    const double p0 = exp(best0 - m);
    const double p1 = exp(best1 - m);
    const double inv = 1.0 / (p0 + p1);
    top_experts[t * 2 + 0] = e0;
    top_experts[t * 2 + 1] = e1;
    top_weights[t * 2 + 0] = p0 * inv;
    top_weights[t * 2 + 1] = p1 * inv;
}

__global__ void moe_ref_up_f64_kernel(
    const float* __restrict__ x,
    const float* __restrict__ w_gate,
    const float* __restrict__ w_up,
    const int32_t* __restrict__ top_experts,
    double* __restrict__ act_buf,
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

    double g_acc = 0.0;
    double u_acc = 0.0;
    for (int h = 0; h < kHiddenDim; ++h) {
        const double xv = static_cast<double>(x_row[h]);
        g_acc += xv * static_cast<double>(wg[h]);
        u_acc += xv * static_cast<double>(wu[h]);
    }
    const double silu_g = g_acc / (1.0 + exp(-g_acc));
    act_buf[static_cast<size_t>(slot) * kInterDim + j] = silu_g * u_acc;
}

__global__ void moe_ref_down_f64_kernel(
    const double* __restrict__ act_buf,
    const float* __restrict__ w_down,
    const int32_t* __restrict__ top_experts,
    const double* __restrict__ top_weights,
    float* __restrict__ y,
    int32_t num_tokens) {
    const int t = blockIdx.x;
    const int h = blockIdx.y * blockDim.x + threadIdx.x;
    if (t >= num_tokens || h >= kHiddenDim) {
        return;
    }
    double out = 0.0;
    for (int r = 0; r < kTopK; ++r) {
        const int slot = t * kTopK + r;
        const int e = top_experts[slot];
        const double w = top_weights[slot];
        const double* a_row = act_buf + static_cast<size_t>(slot) * kInterDim;
        const float* wd = w_down + (static_cast<size_t>(e) * kHiddenDim + h) * kInterDim;
        double acc = 0.0;
        for (int j = 0; j < kInterDim; ++j) {
            acc += a_row[j] * static_cast<double>(wd[j]);
        }
        out += w * acc;
    }
    y[static_cast<size_t>(t) * kHiddenDim + h] = static_cast<float>(out);
}

// Naive unfused baseline kernels (identical algorithm to starter).
__global__ void moe_base_router_kernel(
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
    float best0 = -FLT_MAX, best1 = -FLT_MAX;
    int e0 = 0, e1 = 1;
    for (int e = 0; e < kNumExperts; ++e) {
        const float* rw = router_w + static_cast<size_t>(e) * kHiddenDim;
        float acc = 0.0f;
        for (int h = 0; h < kHiddenDim; ++h) acc += x_row[h] * rw[h];
        if (acc > best0) {
            best1 = best0; e1 = e0; best0 = acc; e0 = e;
        } else if (acc > best1) {
            best1 = acc; e1 = e;
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

__global__ void moe_base_up_kernel(
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
    float g_acc = 0.0f, u_acc = 0.0f;
    for (int h = 0; h < kHiddenDim; ++h) {
        const float xv = x_row[h];
        g_acc += xv * wg[h];
        u_acc += xv * wu[h];
    }
    act_buf[static_cast<size_t>(slot) * kInterDim + j] = (g_acc / (1.0f + expf(-g_acc))) * u_acc;
}

__global__ void moe_base_down_kernel(
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
        for (int j = 0; j < kInterDim; ++j) acc += a_row[j] * wd[j];
        out += w * acc;
    }
    y[static_cast<size_t>(t) * kHiddenDim + h] = out;
}

struct BaselineWorkspace {
    int32_t* top_experts = nullptr;
    float* top_weights = nullptr;
    float* act_buf = nullptr;
    int32_t cap = 0;
    void ensure(int32_t n) {
        if (n <= cap) return;
        cudaFree(top_experts); cudaFree(top_weights); cudaFree(act_buf);
        CUDA_CHECK(cudaMalloc(&top_experts, static_cast<size_t>(n) * kTopK * sizeof(int32_t)));
        CUDA_CHECK(cudaMalloc(&top_weights, static_cast<size_t>(n) * kTopK * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&act_buf, static_cast<size_t>(n) * kTopK * kInterDim * sizeof(float)));
        cap = n;
    }
};

BaselineWorkspace& base_ws() {
    static BaselineWorkspace ws;
    return ws;
}

struct SplitMix64 {
    uint64_t state;
    explicit SplitMix64(uint64_t seed) : state(seed) {}
    uint64_t next_u64() {
        uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    float uniform(float lo, float hi) {
        const double u = static_cast<double>(next_u64() >> 11) * (1.0 / 9007199254740992.0);
        return static_cast<float>(lo + (hi - lo) * u);
    }
};

uint64_t fnv1a_bytes(const void* data, size_t nbytes, uint64_t hash = 14695981039346656037ULL) {
    const auto* ptr = static_cast<const uint8_t*>(data);
    for (size_t i = 0; i < nbytes; ++i) {
        hash ^= static_cast<uint64_t>(ptr[i]);
        hash *= 1099511628211ULL;
    }
    return hash;
}

struct WorkloadSpec {
    std::string name;
    int32_t num_tokens;
    float skew_strength;
    uint64_t seed;
    int warmup_iters;
    int timed_iters;
};

struct WorkloadResult {
    std::string name;
    bool passed;
    bool inputs_immutable;
    double max_abs_err;
    double max_rel_err;
    double baseline_ms;
    double custom_ms;
    double speedup;
};

WorkloadResult run_workload(const WorkloadSpec& spec, bool profile_only, void* d_l2_flush,
                            size_t l2_flush_bytes) {
    const int32_t T = spec.num_tokens;
    SplitMix64 rng(spec.seed);

    const size_t x_elems = static_cast<size_t>(T) * kHiddenDim;
    const size_t rw_elems = static_cast<size_t>(kNumExperts) * kHiddenDim;
    const size_t wg_elems = static_cast<size_t>(kNumExperts) * kInterDim * kHiddenDim;
    const size_t wd_elems = static_cast<size_t>(kNumExperts) * kHiddenDim * kInterDim;

    std::vector<float> h_x(x_elems);
    std::vector<float> h_rw(rw_elems);
    std::vector<float> h_wg(wg_elems);
    std::vector<float> h_wu(wg_elems);
    std::vector<float> h_wd(wd_elems);

    for (float& v : h_x) v = rng.uniform(-0.5f, 0.5f);
    for (int e = 0; e < kNumExperts; ++e) {
        const float bias_scale = (e < 3) ? spec.skew_strength : 0.0f;
        for (int h = 0; h < kHiddenDim; ++h) {
            float val = rng.uniform(-0.15f, 0.15f);
            if (h < 8 && bias_scale > 0.0f) {
                val += bias_scale;
            }
            h_rw[static_cast<size_t>(e) * kHiddenDim + h] = val;
        }
    }
    if (spec.skew_strength > 0.0f) {
        // Align first 8 hidden channels positively on ~65% of tokens to induce realistic hot experts.
        for (int t = 0; t < T; ++t) {
            if ((t % 10) < 7) {
                for (int h = 0; h < 8; ++h) {
                    h_x[static_cast<size_t>(t) * kHiddenDim + h] = rng.uniform(0.3f, 0.9f);
                }
            }
        }
    }
    const float w_scale = 0.08f;
    for (float& v : h_wg) v = rng.uniform(-w_scale, w_scale);
    for (float& v : h_wu) v = rng.uniform(-w_scale, w_scale);
    for (float& v : h_wd) v = rng.uniform(-w_scale, w_scale);

    const size_t x_bytes = x_elems * sizeof(float);
    const size_t rw_bytes = rw_elems * sizeof(float);
    const size_t wg_bytes = wg_elems * sizeof(float);
    const size_t wd_bytes = wd_elems * sizeof(float);

    float *d_x = nullptr, *d_rw = nullptr, *d_wg = nullptr, *d_wu = nullptr, *d_wd = nullptr;
    float *d_y_ref = nullptr, *d_y_custom = nullptr;
    CUDA_CHECK(cudaMalloc(&d_x, x_bytes));
    CUDA_CHECK(cudaMalloc(&d_rw, rw_bytes));
    CUDA_CHECK(cudaMalloc(&d_wg, wg_bytes));
    CUDA_CHECK(cudaMalloc(&d_wu, wg_bytes));
    CUDA_CHECK(cudaMalloc(&d_wd, wd_bytes));
    CUDA_CHECK(cudaMalloc(&d_y_ref, x_bytes));
    CUDA_CHECK(cudaMalloc(&d_y_custom, x_bytes));

    CUDA_CHECK(cudaMemcpy(d_x, h_x.data(), x_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_rw, h_rw.data(), rw_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_wg, h_wg.data(), wg_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_wu, h_wu.data(), wg_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_wd, h_wd.data(), wd_bytes, cudaMemcpyHostToDevice));

    uint64_t expected_hash = fnv1a_bytes(h_x.data(), x_bytes);
    expected_hash = fnv1a_bytes(h_rw.data(), rw_bytes, expected_hash);
    expected_hash = fnv1a_bytes(h_wg.data(), wg_bytes, expected_hash);
    expected_hash = fnv1a_bytes(h_wu.data(), wg_bytes, expected_hash);
    expected_hash = fnv1a_bytes(h_wd.data(), wd_bytes, expected_hash);

    FusedMoeArgs custom_args{d_x, d_rw, d_wg, d_wu, d_wd, d_y_custom, T, 0};

    if (profile_only) {
        launch_fused_moe_custom(custom_args);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaDeviceSynchronize());
        cudaFree(d_x); cudaFree(d_rw); cudaFree(d_wg); cudaFree(d_wu); cudaFree(d_wd);
        cudaFree(d_y_ref); cudaFree(d_y_custom);
        return {spec.name, true, true, 0.0, 0.0, 0.0, 0.0, 1.0};
    }

    // Exact FP64 GPU reference run.
    int32_t* d_ref_exp = nullptr;
    double *d_ref_w = nullptr, *d_ref_act = nullptr;
    CUDA_CHECK(cudaMalloc(&d_ref_exp, static_cast<size_t>(T) * kTopK * sizeof(int32_t)));
    CUDA_CHECK(cudaMalloc(&d_ref_w, static_cast<size_t>(T) * kTopK * sizeof(double)));
    CUDA_CHECK(cudaMalloc(&d_ref_act, static_cast<size_t>(T) * kTopK * kInterDim * sizeof(double)));

    moe_ref_router_f64_kernel<<<(T + 127) / 128, 128>>>(d_x, d_rw, d_ref_exp, d_ref_w, T);
    dim3 ref_up_grid(static_cast<unsigned int>(T * kTopK),
                     static_cast<unsigned int>((kInterDim + 127) / 128));
    moe_ref_up_f64_kernel<<<ref_up_grid, 128>>>(d_x, d_wg, d_wu, d_ref_exp, d_ref_act, T);
    dim3 ref_down_grid(static_cast<unsigned int>(T),
                       static_cast<unsigned int>((kHiddenDim + 127) / 128));
    moe_ref_down_f64_kernel<<<ref_down_grid, 128>>>(d_ref_act, d_wd, d_ref_exp, d_ref_w, d_y_ref, T);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    cudaFree(d_ref_exp); cudaFree(d_ref_w); cudaFree(d_ref_act);

    // Poison custom output before launch.
    CUDA_CHECK(cudaMemset(d_y_custom, 0x7f, x_bytes));
    launch_fused_moe_custom(custom_args);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    // Check input immutability.
    std::vector<float> chk_x(x_elems), chk_rw(rw_elems), chk_wg(wg_elems), chk_wu(wg_elems),
        chk_wd(wd_elems);
    CUDA_CHECK(cudaMemcpy(chk_x.data(), d_x, x_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_rw.data(), d_rw, rw_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_wg.data(), d_wg, wg_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_wu.data(), d_wu, wg_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_wd.data(), d_wd, wd_bytes, cudaMemcpyDeviceToHost));
    uint64_t after_hash = fnv1a_bytes(chk_x.data(), x_bytes);
    after_hash = fnv1a_bytes(chk_rw.data(), rw_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_wg.data(), wg_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_wu.data(), wg_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_wd.data(), wd_bytes, after_hash);
    const bool inputs_immutable = (after_hash == expected_hash);

    std::vector<float> h_y_ref(x_elems), h_y_custom(x_elems);
    CUDA_CHECK(cudaMemcpy(h_y_ref.data(), d_y_ref, x_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(h_y_custom.data(), d_y_custom, x_bytes, cudaMemcpyDeviceToHost));

    const double rtol = 1e-3;
    const double atol = 1e-3;
    double max_abs = 0.0;
    double max_rel = 0.0;
    bool all_ok = inputs_immutable;
    for (size_t i = 0; i < x_elems; ++i) {
        if (!std::isfinite(h_y_custom[i])) {
            all_ok = false;
            max_abs = 1e9;
            max_rel = 1e9;
            break;
        }
        const double diff =
            std::fabs(static_cast<double>(h_y_custom[i]) - static_cast<double>(h_y_ref[i]));
        const double denom = std::max(std::fabs(static_cast<double>(h_y_ref[i])), 1e-6);
        max_abs = std::max(max_abs, diff);
        max_rel = std::max(max_rel, diff / denom);
        if (diff > atol + rtol * std::fabs(static_cast<double>(h_y_ref[i]))) {
            all_ok = false;
        }
    }

    // L2-flushed CUDA-event median timing.
    cudaEvent_t ev_start = nullptr, ev_stop = nullptr;
    CUDA_CHECK(cudaEventCreate(&ev_start));
    CUDA_CHECK(cudaEventCreate(&ev_stop));

    auto measure_ms = [&](auto fn, const FusedMoeArgs& call_args) -> double {
        for (int i = 0; i < spec.warmup_iters; ++i) {
            fn(call_args);
        }
        CUDA_CHECK(cudaDeviceSynchronize());
        std::vector<double> samples;
        samples.reserve(static_cast<size_t>(spec.timed_iters));
        for (int i = 0; i < spec.timed_iters; ++i) {
            CUDA_CHECK(cudaMemset(d_l2_flush, i & 0xff, l2_flush_bytes));
            CUDA_CHECK(cudaDeviceSynchronize());
            CUDA_CHECK(cudaEventRecord(ev_start));
            fn(call_args);
            CUDA_CHECK(cudaEventRecord(ev_stop));
            CUDA_CHECK(cudaEventSynchronize(ev_stop));
            CUDA_CHECK(cudaGetLastError());
            float ms = 0.0f;
            CUDA_CHECK(cudaEventElapsedTime(&ms, ev_start, ev_stop));
            samples.push_back(static_cast<double>(ms));
        }
        std::sort(samples.begin(), samples.end());
        return samples[samples.size() / 2];
    };

    FusedMoeArgs base_args = custom_args;
    base_args.y = d_y_ref;
    const double baseline_ms = measure_ms(launch_fused_moe_baseline, base_args);
    const double custom_ms = measure_ms(launch_fused_moe_custom, custom_args);
    const double speedup = (custom_ms > 0.0) ? (baseline_ms / custom_ms) : 0.0;

    CUDA_CHECK(cudaEventDestroy(ev_start));
    CUDA_CHECK(cudaEventDestroy(ev_stop));
    cudaFree(d_x); cudaFree(d_rw); cudaFree(d_wg); cudaFree(d_wu); cudaFree(d_wd);
    cudaFree(d_y_ref); cudaFree(d_y_custom);

    return {spec.name, all_ok, inputs_immutable, max_abs, max_rel, baseline_ms, custom_ms, speedup};
}

}  // namespace

void launch_fused_moe_baseline(const FusedMoeArgs& args) {
    if (args.num_tokens <= 0) {
        return;
    }
    auto& ws = base_ws();
    ws.ensure(args.num_tokens);
    moe_base_router_kernel<<<(args.num_tokens + 127) / 128, 128, 0, args.stream>>>(
        args.x, args.router_w, ws.top_experts, ws.top_weights, args.num_tokens);
    dim3 up_grid(static_cast<unsigned int>(args.num_tokens * kTopK),
                 static_cast<unsigned int>((kInterDim + 127) / 128));
    moe_base_up_kernel<<<up_grid, 128, 0, args.stream>>>(
        args.x, args.w_gate, args.w_up, ws.top_experts, ws.act_buf, args.num_tokens);
    dim3 down_grid(static_cast<unsigned int>(args.num_tokens),
                   static_cast<unsigned int>((kHiddenDim + 127) / 128));
    moe_base_down_kernel<<<down_grid, 128, 0, args.stream>>>(
        ws.act_buf, args.w_down, ws.top_experts, ws.top_weights, args.y, args.num_tokens);
}

}  // namespace moe

int main(int argc, char** argv) {
    bool json_out = false;
    bool profile_only = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--json") == 0) {
            json_out = true;
        } else if (std::strcmp(argv[i], "--profile-only") == 0) {
            profile_only = true;
        }
    }

    const size_t l2_flush_bytes = 64ULL * 1024ULL * 1024ULL;
    void* d_l2_flush = nullptr;
    CUDA_CHECK(cudaMalloc(&d_l2_flush, l2_flush_bytes));

    std::vector<moe::WorkloadSpec> workloads = {
        {"moe_skewed_512", 512, 0.35f, 1101ULL, 2, 7},
        {"moe_balanced_1024", 1024, 0.0f, 1202ULL, 2, 5},
    };
#ifdef EXTENDED_SHAPES
    workloads.push_back({"extended_small_odd_37", 37, 0.50f, 1303ULL, 2, 7});
    workloads.push_back({"extended_heavy_skew_1536", 1536, 0.55f, 1404ULL, 2, 5});
#endif

    if (profile_only) {
        moe::run_workload(workloads[0], true, d_l2_flush, l2_flush_bytes);
        cudaFree(d_l2_flush);
        return 0;
    }

    std::vector<moe::WorkloadResult> results;
    results.reserve(workloads.size());
    bool all_passed = true;
    bool all_immutable = true;
    double log_speedup_sum = 0.0;

    for (const auto& w : workloads) {
        auto r = moe::run_workload(w, false, d_l2_flush, l2_flush_bytes);
        all_passed = all_passed && r.passed;
        all_immutable = all_immutable && r.inputs_immutable;
        log_speedup_sum += std::log(std::max(r.speedup, 1e-6));
        results.push_back(r);
    }
    const double geomean_speedup = std::exp(log_speedup_sum / static_cast<double>(results.size()));
    cudaFree(d_l2_flush);

    if (json_out) {
        printf("{\n");
        printf("  \"problem\": \"fused_moe\",\n");
        printf("  \"passed\": %s,\n", all_passed ? "true" : "false");
        printf("  \"inputs_immutable\": %s,\n", all_immutable ? "true" : "false");
        printf("  \"geomean_speedup\": %.4f,\n", geomean_speedup);
        printf("  \"workloads\": [\n");
        for (size_t i = 0; i < results.size(); ++i) {
            const auto& r = results[i];
            printf(
                "    {\"name\": \"%s\", \"passed\": %s, \"inputs_immutable\": %s, "
                "\"max_abs_err\": %.6e, \"max_rel_err\": %.6e, "
                "\"baseline_ms\": %.4f, \"custom_ms\": %.4f, \"speedup\": %.4f}%s\n",
                r.name.c_str(),
                r.passed ? "true" : "false",
                r.inputs_immutable ? "true" : "false",
                r.max_abs_err,
                r.max_rel_err,
                r.baseline_ms,
                r.custom_ms,
                r.speedup,
                (i + 1 < results.size()) ? "," : "");
        }
        printf("  ]\n");
        printf("}\n");
    } else {
        printf("Fused MoE Results (geomean speedup: %.2fx, passed=%s)\n",
               geomean_speedup, all_passed ? "YES" : "NO");
        for (const auto& r : results) {
            printf("  %-24s pass=%-3s immut=%-3s abs=%.2e rel=%.2e base=%.3fms custom=%.3fms speedup=%.2fx\n",
                   r.name.c_str(),
                   r.passed ? "YES" : "NO",
                   r.inputs_immutable ? "YES" : "NO",
                   r.max_abs_err,
                   r.max_rel_err,
                   r.baseline_ms,
                   r.custom_ms,
                   r.speedup);
        }
    }

    return all_passed ? 0 : 1;
}
