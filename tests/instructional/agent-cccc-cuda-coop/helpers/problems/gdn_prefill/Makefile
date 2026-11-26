NVCC ?= nvcc
ARCH ?= sm_121
NVCC_FLAGS ?= -O3 -std=c++17 -arch=$(ARCH) --use_fast_math
NCU ?= ncu
NSYS ?= nsys

.PHONY: build run run-json profile-ncu profile-nsys clean

build: run_kernel

run_kernel: driver.cu solution.cu kernel_api.cuh
	$(NVCC) $(NVCC_FLAGS) driver.cu solution.cu -o run_kernel

run: build
	./run_kernel

run-json: build
	./run_kernel --json

profile-ncu: build
	$(NCU) --metrics sm__throughput.avg.pct_of_peak_sustained_elapsed,dram__throughput.avg.pct_of_peak_sustained_elapsed,sm__warps_active.avg.pct_of_peak_sustained_active,launch__registers_per_thread ./run_kernel --profile-only

profile-nsys: build
	$(NSYS) profile --stats=true --force-overwrite=true -o profile_trace ./run_kernel --profile-only

clean:
	rm -f run_kernel profile_trace.nsys-rep profile_trace.sqlite
