#include "kernel_api.cuh"

#include <algorithm>
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

namespace gdn {
namespace {

__device__ __forceinline__ float dev_softplus_f32(float x) {
    return (x > 20.0f) ? x : log1pf(expf(x));
}

__device__ __forceinline__ double dev_softplus_f64(double x) {
    return (x > 30.0) ? x : log1p(exp(x));
}

// Authoritative double-precision GPU reference kernel for exact ground truth.
__global__ void gdn_prefill_ref_f64_kernel(
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
    double scale) {
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

    double s_reg[kHeadDim];
    if (init_state != nullptr) {
        const float* init_row = init_state + state_base + static_cast<size_t>(v_idx) * kHeadDim;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_reg[ki] = static_cast<double>(init_row[ki]);
        }
    } else {
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_reg[ki] = 0.0;
        }
    }

    const double exp_a_log = exp(static_cast<double>(a_log[hv]));
    const double bias = static_cast<double>(dt_bias[hv]);

    for (int t = seq_start; t < seq_end; ++t) {
        const double a_val = static_cast<double>(a[static_cast<size_t>(t) * kNumVHeads + hv]);
        const double b_val = static_cast<double>(b[static_cast<size_t>(t) * kNumVHeads + hv]);
        const double g = exp(-exp_a_log * dev_softplus_f64(a_val + bias));
        const double beta = 1.0 / (1.0 + exp(-b_val));

        const float* k_ptr = k + (static_cast<size_t>(t) * kNumQKHeads + hqk) * kHeadDim;
        const float* q_ptr = q + (static_cast<size_t>(t) * kNumQKHeads + hqk) * kHeadDim;
        const double v_val = static_cast<double>(
            v[(static_cast<size_t>(t) * kNumVHeads + hv) * kHeadDim + v_idx]);

        double pred = 0.0;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_reg[ki] *= g;
            pred += s_reg[ki] * static_cast<double>(k_ptr[ki]);
        }

        const double delta = beta * (v_val - pred);
        double out_acc = 0.0;
        for (int ki = 0; ki < kHeadDim; ++ki) {
            s_reg[ki] += delta * static_cast<double>(k_ptr[ki]);
            out_acc += s_reg[ki] * static_cast<double>(q_ptr[ki]);
        }

        output[(static_cast<size_t>(t) * kNumVHeads + hv) * kHeadDim + v_idx] =
            static_cast<float>(scale * out_acc);
    }

    float* out_row = new_state + state_base + static_cast<size_t>(v_idx) * kHeadDim;
    for (int ki = 0; ki < kHeadDim; ++ki) {
        out_row[ki] = static_cast<float>(s_reg[ki]);
    }
}

// Naive global-memory sequential baseline (matches starter).
__global__ void gdn_prefill_baseline_kernel(
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
        const float g = expf(-exp_a_log * dev_softplus_f32(a_val + bias));
        const float beta = 1.0f / (1.0f + expf(-b_val));

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
    std::vector<int32_t> cu_seqlens;
    bool with_init_state;
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

void normalize_head_vectors(std::vector<float>& buf, int count) {
    for (int i = 0; i < count; ++i) {
        float* row = buf.data() + static_cast<size_t>(i) * kHeadDim;
        double norm_sq = 0.0;
        for (int d = 0; d < kHeadDim; ++d) {
            norm_sq += static_cast<double>(row[d]) * static_cast<double>(row[d]);
        }
        const float inv = static_cast<float>(1.0 / sqrt(norm_sq + 1e-6));
        for (int d = 0; d < kHeadDim; ++d) {
            row[d] *= inv;
        }
    }
}

WorkloadResult run_workload(const WorkloadSpec& spec, bool profile_only, void* d_l2_flush,
                            size_t l2_flush_bytes) {
    const int32_t num_seqs = static_cast<int32_t>(spec.cu_seqlens.size()) - 1;
    const int32_t total_tokens = spec.cu_seqlens.back();
    const float scale = 1.0f / sqrtf(static_cast<float>(kHeadDim));

    SplitMix64 rng(spec.seed);
    std::vector<float> h_q(static_cast<size_t>(total_tokens) * kNumQKHeads * kHeadDim);
    std::vector<float> h_k(static_cast<size_t>(total_tokens) * kNumQKHeads * kHeadDim);
    std::vector<float> h_v(static_cast<size_t>(total_tokens) * kNumVHeads * kHeadDim);
    std::vector<float> h_a_log(kNumVHeads);
    std::vector<float> h_a(static_cast<size_t>(total_tokens) * kNumVHeads);
    std::vector<float> h_dt_bias(kNumVHeads);
    std::vector<float> h_b(static_cast<size_t>(total_tokens) * kNumVHeads);
    std::vector<float> h_init_state;

    for (float& x : h_q) x = rng.uniform(-1.0f, 1.0f);
    for (float& x : h_k) x = rng.uniform(-1.0f, 1.0f);
    normalize_head_vectors(h_q, total_tokens * kNumQKHeads);
    normalize_head_vectors(h_k, total_tokens * kNumQKHeads);
    for (float& x : h_v) x = rng.uniform(-0.75f, 0.75f);
    for (float& x : h_a_log) x = rng.uniform(-2.5f, -0.5f);
    for (float& x : h_a) x = rng.uniform(-1.5f, 1.5f);
    for (float& x : h_dt_bias) x = rng.uniform(-1.0f, 0.5f);
    for (float& x : h_b) x = rng.uniform(-1.5f, 1.5f);
    if (spec.with_init_state) {
        h_init_state.resize(static_cast<size_t>(num_seqs) * kNumVHeads * kHeadDim * kHeadDim);
        for (float& x : h_init_state) x = rng.uniform(-0.15f, 0.15f);
    }

    const size_t q_bytes = h_q.size() * sizeof(float);
    const size_t k_bytes = h_k.size() * sizeof(float);
    const size_t v_bytes = h_v.size() * sizeof(float);
    const size_t alog_bytes = h_a_log.size() * sizeof(float);
    const size_t a_bytes = h_a.size() * sizeof(float);
    const size_t dt_bytes = h_dt_bias.size() * sizeof(float);
    const size_t b_bytes = h_b.size() * sizeof(float);
    const size_t cu_bytes = spec.cu_seqlens.size() * sizeof(int32_t);
    const size_t state_elems =
        static_cast<size_t>(num_seqs) * kNumVHeads * kHeadDim * kHeadDim;
    const size_t state_bytes = state_elems * sizeof(float);
    const size_t out_elems = static_cast<size_t>(total_tokens) * kNumVHeads * kHeadDim;
    const size_t out_bytes = out_elems * sizeof(float);

    float *d_q = nullptr, *d_k = nullptr, *d_v = nullptr, *d_init = nullptr;
    float *d_a_log = nullptr, *d_a = nullptr, *d_dt_bias = nullptr, *d_b = nullptr;
    int32_t* d_cu = nullptr;
    float *d_out_ref = nullptr, *d_state_ref = nullptr;
    float *d_out_custom = nullptr, *d_state_custom = nullptr;

    CUDA_CHECK(cudaMalloc(&d_q, std::max<size_t>(q_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_k, std::max<size_t>(k_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_v, std::max<size_t>(v_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_a_log, alog_bytes));
    CUDA_CHECK(cudaMalloc(&d_a, std::max<size_t>(a_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_dt_bias, dt_bytes));
    CUDA_CHECK(cudaMalloc(&d_b, std::max<size_t>(b_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_cu, cu_bytes));
    CUDA_CHECK(cudaMalloc(&d_out_ref, std::max<size_t>(out_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_state_ref, std::max<size_t>(state_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_out_custom, std::max<size_t>(out_bytes, 4)));
    CUDA_CHECK(cudaMalloc(&d_state_custom, std::max<size_t>(state_bytes, 4)));
    if (spec.with_init_state) {
        CUDA_CHECK(cudaMalloc(&d_init, std::max<size_t>(state_bytes, 4)));
        CUDA_CHECK(cudaMemcpy(d_init, h_init_state.data(), state_bytes, cudaMemcpyHostToDevice));
    }

    if (q_bytes > 0) CUDA_CHECK(cudaMemcpy(d_q, h_q.data(), q_bytes, cudaMemcpyHostToDevice));
    if (k_bytes > 0) CUDA_CHECK(cudaMemcpy(d_k, h_k.data(), k_bytes, cudaMemcpyHostToDevice));
    if (v_bytes > 0) CUDA_CHECK(cudaMemcpy(d_v, h_v.data(), v_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_a_log, h_a_log.data(), alog_bytes, cudaMemcpyHostToDevice));
    if (a_bytes > 0) CUDA_CHECK(cudaMemcpy(d_a, h_a.data(), a_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_dt_bias, h_dt_bias.data(), dt_bytes, cudaMemcpyHostToDevice));
    if (b_bytes > 0) CUDA_CHECK(cudaMemcpy(d_b, h_b.data(), b_bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_cu, spec.cu_seqlens.data(), cu_bytes, cudaMemcpyHostToDevice));

    uint64_t expected_input_hash = fnv1a_bytes(h_q.data(), q_bytes);
    expected_input_hash = fnv1a_bytes(h_k.data(), k_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(h_v.data(), v_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(h_a_log.data(), alog_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(h_a.data(), a_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(h_dt_bias.data(), dt_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(h_b.data(), b_bytes, expected_input_hash);
    expected_input_hash = fnv1a_bytes(spec.cu_seqlens.data(), cu_bytes, expected_input_hash);
    if (spec.with_init_state) {
        expected_input_hash = fnv1a_bytes(h_init_state.data(), state_bytes, expected_input_hash);
    }

    GdnPrefillArgs custom_args{
        d_q, d_k, d_v, d_init, d_a_log, d_a, d_dt_bias, d_b, d_cu,
        d_out_custom, d_state_custom, num_seqs, total_tokens, scale, 0};

    if (profile_only) {
        launch_gdn_prefill_custom(custom_args);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaDeviceSynchronize());
        cudaFree(d_q); cudaFree(d_k); cudaFree(d_v); cudaFree(d_init);
        cudaFree(d_a_log); cudaFree(d_a); cudaFree(d_dt_bias); cudaFree(d_b);
        cudaFree(d_cu); cudaFree(d_out_ref); cudaFree(d_state_ref);
        cudaFree(d_out_custom); cudaFree(d_state_custom);
        return {spec.name, true, true, 0.0, 0.0, 0.0, 0.0, 1.0};
    }

    // Exact FP64 reference run.
    dim3 grid(static_cast<unsigned int>(num_seqs), static_cast<unsigned int>(kNumVHeads));
    dim3 block(static_cast<unsigned int>(kHeadDim));
    gdn_prefill_ref_f64_kernel<<<grid, block>>>(
        d_q, d_k, d_v, d_init, d_a_log, d_a, d_dt_bias, d_b, d_cu,
        d_out_ref, d_state_ref, static_cast<double>(scale));
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    // Fill custom outputs with poison pattern before custom launch.
    CUDA_CHECK(cudaMemset(d_out_custom, 0x7f, std::max<size_t>(out_bytes, 4)));
    CUDA_CHECK(cudaMemset(d_state_custom, 0x7f, std::max<size_t>(state_bytes, 4)));

    launch_gdn_prefill_custom(custom_args);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    // Check input immutability.
    std::vector<float> chk_q(h_q.size()), chk_k(h_k.size()), chk_v(h_v.size());
    std::vector<float> chk_alog(h_a_log.size()), chk_a(h_a.size()), chk_dt(h_dt_bias.size()),
        chk_b(h_b.size());
    std::vector<int32_t> chk_cu(spec.cu_seqlens.size());
    std::vector<float> chk_init(h_init_state.size());
    if (q_bytes > 0) CUDA_CHECK(cudaMemcpy(chk_q.data(), d_q, q_bytes, cudaMemcpyDeviceToHost));
    if (k_bytes > 0) CUDA_CHECK(cudaMemcpy(chk_k.data(), d_k, k_bytes, cudaMemcpyDeviceToHost));
    if (v_bytes > 0) CUDA_CHECK(cudaMemcpy(chk_v.data(), d_v, v_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_alog.data(), d_a_log, alog_bytes, cudaMemcpyDeviceToHost));
    if (a_bytes > 0) CUDA_CHECK(cudaMemcpy(chk_a.data(), d_a, a_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_dt.data(), d_dt_bias, dt_bytes, cudaMemcpyDeviceToHost));
    if (b_bytes > 0) CUDA_CHECK(cudaMemcpy(chk_b.data(), d_b, b_bytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(chk_cu.data(), d_cu, cu_bytes, cudaMemcpyDeviceToHost));
    if (spec.with_init_state) {
        CUDA_CHECK(cudaMemcpy(chk_init.data(), d_init, state_bytes, cudaMemcpyDeviceToHost));
    }
    uint64_t after_hash = fnv1a_bytes(chk_q.data(), q_bytes);
    after_hash = fnv1a_bytes(chk_k.data(), k_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_v.data(), v_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_alog.data(), alog_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_a.data(), a_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_dt.data(), dt_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_b.data(), b_bytes, after_hash);
    after_hash = fnv1a_bytes(chk_cu.data(), cu_bytes, after_hash);
    if (spec.with_init_state) {
        after_hash = fnv1a_bytes(chk_init.data(), state_bytes, after_hash);
    }
    const bool inputs_immutable = (after_hash == expected_input_hash);

    // Compare outputs and final states against FP64 reference.
    std::vector<float> h_out_ref(out_elems), h_out_custom(out_elems);
    std::vector<float> h_state_ref(state_elems), h_state_custom(state_elems);
    if (out_bytes > 0) {
        CUDA_CHECK(cudaMemcpy(h_out_ref.data(), d_out_ref, out_bytes, cudaMemcpyDeviceToHost));
        CUDA_CHECK(
            cudaMemcpy(h_out_custom.data(), d_out_custom, out_bytes, cudaMemcpyDeviceToHost));
    }
    if (state_bytes > 0) {
        CUDA_CHECK(
            cudaMemcpy(h_state_ref.data(), d_state_ref, state_bytes, cudaMemcpyDeviceToHost));
        CUDA_CHECK(
            cudaMemcpy(h_state_custom.data(), d_state_custom, state_bytes, cudaMemcpyDeviceToHost));
    }

    const double rtol = 1e-3;
    const double atol = 1e-3;
    double max_abs = 0.0;
    double max_rel = 0.0;
    bool all_ok = inputs_immutable;

    auto compare_vec = [&](const std::vector<float>& ref, const std::vector<float>& got) {
        for (size_t i = 0; i < ref.size(); ++i) {
            if (!std::isfinite(got[i])) {
                all_ok = false;
                max_abs = 1e9;
                max_rel = 1e9;
                return;
            }
            const double diff = std::fabs(static_cast<double>(got[i]) - static_cast<double>(ref[i]));
            const double denom = std::max(std::fabs(static_cast<double>(ref[i])), 1e-6);
            max_abs = std::max(max_abs, diff);
            max_rel = std::max(max_rel, diff / denom);
            if (diff > atol + rtol * std::fabs(static_cast<double>(ref[i]))) {
                all_ok = false;
            }
        }
    };
    compare_vec(h_out_ref, h_out_custom);
    compare_vec(h_state_ref, h_state_custom);

    // L2-flushed CUDA-event median timing for baseline and custom.
    cudaEvent_t ev_start = nullptr, ev_stop = nullptr;
    CUDA_CHECK(cudaEventCreate(&ev_start));
    CUDA_CHECK(cudaEventCreate(&ev_stop));

    auto measure_ms = [&](auto fn, const GdnPrefillArgs& call_args) -> double {
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

    GdnPrefillArgs base_args = custom_args;
    base_args.output = d_out_ref;
    base_args.new_state = d_state_ref;

    const double baseline_ms = measure_ms(launch_gdn_prefill_baseline, base_args);
    const double custom_ms = measure_ms(launch_gdn_prefill_custom, custom_args);
    const double speedup = (custom_ms > 0.0) ? (baseline_ms / custom_ms) : 0.0;

    CUDA_CHECK(cudaEventDestroy(ev_start));
    CUDA_CHECK(cudaEventDestroy(ev_stop));
    cudaFree(d_q); cudaFree(d_k); cudaFree(d_v); cudaFree(d_init);
    cudaFree(d_a_log); cudaFree(d_a); cudaFree(d_dt_bias); cudaFree(d_b);
    cudaFree(d_cu); cudaFree(d_out_ref); cudaFree(d_state_ref);
    cudaFree(d_out_custom); cudaFree(d_state_custom);

    return {spec.name, all_ok, inputs_immutable, max_abs, max_rel, baseline_ms, custom_ms, speedup};
}

}  // namespace

void launch_gdn_prefill_baseline(const GdnPrefillArgs& args) {
    if (args.num_seqs <= 0) {
        return;
    }
    const float scale = (args.scale > 0.0f) ? args.scale : (1.0f / sqrtf(static_cast<float>(kHeadDim)));
    dim3 grid(static_cast<unsigned int>(args.num_seqs), static_cast<unsigned int>(kNumVHeads));
    dim3 block(static_cast<unsigned int>(kHeadDim));
    gdn_prefill_baseline_kernel<<<grid, block, 0, args.stream>>>(
        args.q, args.k, args.v, args.init_state, args.a_log, args.a, args.dt_bias, args.b,
        args.cu_seqlens, args.output, args.new_state, scale);
}

}  // namespace gdn

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

    std::vector<gdn::WorkloadSpec> workloads = {
        {"prefill_balanced", {0, 256, 512, 768, 1024}, false, 101ULL, 2, 7},
        {"prefill_ragged_init", {0, 73, 329, 456, 987}, true, 202ULL, 2, 7},
        {"prefill_long", {0, 1024, 2048}, false, 303ULL, 2, 5},
    };
#ifdef EXTENDED_SHAPES
    workloads.push_back({"extended_odd_tail", {0, 1, 17, 145, 513, 899}, true, 404ULL, 2, 5});
    workloads.push_back({"extended_empty_and_long", {0, 0, 640, 640, 1536}, true, 505ULL, 2, 5});
#endif

    if (profile_only) {
        gdn::run_workload(workloads[0], true, d_l2_flush, l2_flush_bytes);
        cudaFree(d_l2_flush);
        return 0;
    }

    std::vector<gdn::WorkloadResult> results;
    results.reserve(workloads.size());
    bool all_passed = true;
    bool all_immutable = true;
    double log_speedup_sum = 0.0;

    for (const auto& w : workloads) {
        auto r = gdn::run_workload(w, false, d_l2_flush, l2_flush_bytes);
        all_passed = all_passed && r.passed;
        all_immutable = all_immutable && r.inputs_immutable;
        log_speedup_sum += std::log(std::max(r.speedup, 1e-6));
        results.push_back(r);
    }
    const double geomean_speedup = std::exp(log_speedup_sum / static_cast<double>(results.size()));
    cudaFree(d_l2_flush);

    if (json_out) {
        printf("{\n");
        printf("  \"problem\": \"gdn_prefill\",\n");
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
        printf("GDN Prefill Results (geomean speedup: %.2fx, passed=%s)\n",
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
