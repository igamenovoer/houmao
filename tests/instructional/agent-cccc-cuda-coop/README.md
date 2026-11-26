# Instructional Four-Agent CCCC CUDA Cooperation Suite

Status: draft

Agent-driven live verification for four Houmao-managed Web agents (`lead`, `algo`, `kernel`, `profiler`) collaborating exclusively through one `houmao-cccc` Group on a standalone CUDA optimization problem. The two problems use CUDA C++ and native tools (`nvcc`, `ncu`, `nsys`). Choose `gdn_prefill` (Gated Delta Net prefill, default) or `fused_moe` (Fused Top-K MoE SwiGLU block). [Problem manifest](manifest.toml)

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved through `git rev-parse --show-toplevel`).
- **Manager and plugin.** Use matching workspace builds of `houmao-mgr` and `houmao-cccc` with receiver protocol 2 support. Set `HOUMAO_MGR` and `HOUMAO_CCCC` to those two executables (default `$REPO_ROOT/.pixi/envs/default/bin/`).
- **Model pool.** Configure your private external model pool with entries that support managed `web` mode and provide each client's executable and model settings as needed. Set `HOUMAO_TEST_MODEL` to one key for all four slots, or assign individual keys with `HOUMAO_TEST_MODEL_LEAD`, `HOUMAO_TEST_MODEL_ALGO`, `HOUMAO_TEST_MODEL_KERNEL`, and `HOUMAO_TEST_MODEL_PROFILER`. A per-slot key takes precedence over `HOUMAO_TEST_MODEL`. See the [test fixture guide](../../../scripts/agents/test-fixtures/README.md).
- **CUDA toolchain & GPU.** Local NVIDIA GPU visible to `nvidia-smi` (target architecture auto-detected from compute capability, e.g., `sm_121` on NVIDIA GB10, or pinned via `[cuda].arch` in `manifest.toml`), plus working `nvcc`, `ncu`, `nsys`, and `g++`. No Python ML packages are required.
- **CCCC service.** Set `CCCC_ENDPOINT` to a running external-receiver protocol-2 service. For local managed services, set `CCCC_SERVICE_RUNTIME` and `CCCC_PROVIDER_BINARY` so `configure` and `doctor` verify the PID, `/proc` executable, build receipt, protocol 2, tracked patch series, and binary SHA-256. Omit both for remote services.
- **Private external root.** Houmao forbids plugin credentials inside the checkout. Set `CCCC_PRIVATE_ROOT` to an owner-private directory outside `$REPO_ROOT` (default `$HOME/.local/state/houmao/cccc-instructional`). `configure` writes one run-specific subdirectory with four grant files and `stop` deletes only those four files.
- **Project-local temporary root.** `$REPO_ROOT/tmp/instructional-tests/<test-slug>/` (Git-ignored). Holds temporary `scripts/`, disposable `runtime/` (four fixture homes, the shared agent-writable `cuda-workspace/`, and the clean runner-owned `independent-verify/` build dir), `run-meta.json`, and surviving `evidence/agent-cccc-cuda-coop/<scenario-slug>/`.
- **Isolation.** Each of the four agents prepares with `--tmux-server new` and owns an isolated tmux socket, registry, runtime root, home, gateway port, Houmao UUID, and CCCC Actor grant inside one run-unique Group. Never touch the caller's default tmux server or another Group.
- **Single-GPU concurrency rule.** Do not run two CUDA cooperation bundles concurrently against the same local GPU; concurrent `ncu` runs serialize and skew timing.
- **Operator recovery channel.** `configure` registers one run-local offline filesystem mailbox per agent. `recovery-post` is strictly for operator recovery after a failure, requires `--confirm-operator-recovery`, and invalidates the graded run.

## Launch

Ensure workspace binaries are current:

```bash
pixi install
pixi run python scripts/agents/test-fixtures/fixture.py list-models
```

Allocate the isolated run workspace, inspect the resolved manifest, and verify live preconditions (set `PROBLEM_ID=gdn_prefill` by default, or `PROBLEM_ID=fused_moe` to switch problems):

```bash
umask 077
unset TMUX TMUX_PANE TMUX_TMPDIR
export REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
export BUNDLE_ROOT="$REPO_ROOT/tests/instructional/agent-cccc-cuda-coop"
export MANIFEST="$BUNDLE_ROOT/manifest.toml"
export FIXTURE="$REPO_ROOT/scripts/agents/test-fixtures/fixture.py"
export PROBLEM_ID="${PROBLEM_ID:-gdn_prefill}"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-agent-cccc-cuda-coop-${PROBLEM_ID}"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export EVIDENCE="$RUN_TMP/evidence/agent-cccc-cuda-coop"
export RUN_META="$RUN_TMP/run-meta.json"
export WORKSPACE_DIR="$RUN_TMP/runtime/cuda-workspace"
export HOUMAO_MGR="${HOUMAO_MGR:-$REPO_ROOT/.pixi/envs/default/bin/houmao-mgr}"
export HOUMAO_CCCC="${HOUMAO_CCCC:-$REPO_ROOT/.pixi/envs/default/bin/houmao-cccc}"
export CCCC_ENDPOINT="${CCCC_ENDPOINT:?Set the receiver v2 service endpoint}"
export CCCC_SERVICE_RUNTIME="${CCCC_SERVICE_RUNTIME:-$HOME/.local/share/houmao-cccc-receiver-v2-queue/runtime.json}"
export CCCC_PROVIDER_BINARY="${CCCC_PROVIDER_BINARY:-$HOME/.local/share/houmao-cccc-receiver-v2-queue/target/debug/cccc}"
export CCCC_PRIVATE_ROOT="${CCCC_PRIVATE_ROOT:-$HOME/.local/state/houmao/cccc-instructional}"

mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime" "$EVIDENCE"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored" >&2; exit 1; }
chmod 700 "$RUN_TMP"
test -x "$HOUMAO_MGR" && test -x "$HOUMAO_CCCC"
curl -fsS "$CCCC_ENDPOINT/api/v1/health" >/dev/null
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" show-manifest \
  --manifest "$MANIFEST" --problem "$PROBLEM_ID" > "$EVIDENCE/manifest-resolved.json"

for ROLE in lead algo kernel profiler; do
  pixi run python "$FIXTURE" check \
    --pool-slot "$ROLE" --mode web --surface manager --live \
    > "$EVIDENCE/$ROLE-check.json" || exit 1
done
```

The fixture preflight probes the configured API route or validates the selected native-login import. Review the output for each role before preparation.

Prepare, launch, and seed all four managed Web agents. The fixture applies the reasoning preset from each selected pool entry during preparation when that entry declares one.

```bash
for ROLE in lead algo kernel profiler; do
  mkdir -p "$RUN_TMP/runtime/runs-$ROLE"
  pixi run python "$FIXTURE" prepare \
    --pool-slot "$ROLE" --mode web --surface manager \
    --prompt-mode unattended --tmux-server new \
    --role "cuda-$ROLE" --system-prompt-file "$BUNDLE_ROOT/helpers/roles/$ROLE.md" \
    --run-root "$RUN_TMP/runtime/runs-$ROLE" > "$EVIDENCE/$ROLE-prepare.json" || exit 1
  RUN_DIR="$(jq -er '.run_dir' "$EVIDENCE/$ROLE-prepare.json")" || exit 1
  pixi run python "$FIXTURE" launch --run-dir "$RUN_DIR" \
    > "$EVIDENCE/$ROLE-launch.json" || exit 1
  pixi run python "$FIXTURE" prompt \
    --run-dir "$RUN_DIR" --prompt "Confirm your role is $ROLE and reply with the single word ready." \
    > "$EVIDENCE/$ROLE-seed.json" || exit 1
done

export RUN_LEAD="$(jq -r '.run_dir' "$EVIDENCE/lead-prepare.json")"
export RUN_ALGO="$(jq -r '.run_dir' "$EVIDENCE/algo-prepare.json")"
export RUN_KERNEL="$(jq -r '.run_dir' "$EVIDENCE/kernel-prepare.json")"
export RUN_PROFILER="$(jq -r '.run_dir' "$EVIDENCE/profiler-prepare.json")"
```

Provision the four-actor CCCC Group, seed the shared CUDA workspace from `manifest.toml`, register operator recovery mailboxes, and attach all four gateways preserving native bodies:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" configure \
  --manifest "$MANIFEST" --problem "$PROBLEM_ID" \
  --run-lead "$RUN_LEAD" --run-algo "$RUN_ALGO" \
  --run-kernel "$RUN_KERNEL" --run-profiler "$RUN_PROFILER" \
  --endpoint "$CCCC_ENDPOINT" \
  --service-runtime "$CCCC_SERVICE_RUNTIME" --provider-binary "$CCCC_PROVIDER_BINARY" \
  --private-root "$CCCC_PRIVATE_ROOT" --workspace-dir "$WORKSPACE_DIR" \
  --run-meta "$RUN_META" --evidence-root "$EVIDENCE" > "$EVIDENCE/configure.json"
```

## Doctor

Run Doctor before the first scenario drive, on every fresh launch, and after any failed or surprising drive:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" doctor \
  --run-meta "$RUN_META" | tee "$EVIDENCE/doctor.json"
```

Doctor exits zero only when the selected `manifest.toml` problem and seeded workspace files exist, `nvidia-smi` / `nvcc` / `ncu` / `nsys` are healthy, the CCCC service identity and health check pass, all four gateways and native bodies are healthy and unchanged from pre-attachment snapshots, all four CCCC bindings are connected to the same four-member Group, and all four operator recovery mailboxes are registered.

`configure` records each role's `pool_key` and `pool_slot` under `model_pool` in `run-meta.json`. Doctor checks them against the prepared fixture and prints both fields under `agents.<role>`.

## Drive

Set the effective delivery policy across all four agents (default from `manifest.toml` is timed push batching so multi-peer updates arrive in compact request fences without turn thrashing):

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" delivery \
  --run-meta "$RUN_META" --role all --policy batch --quiet-interval 6 --max-wait 15 \
  > "$EVIDENCE/delivery.json"
```

Kick off the optimization task by sending one organic operator prompt to `lead` (see the scenario files under `cases/`). Let the four agents coordinate autonomously over CCCC chat, then wait for quiescence via `wait-idle` rather than a blind fixed sleep. Never relay messages on behalf of agents or hand-hold CCCC CLI commands in operator prompts.

## Evidence

Keep the preflight and configuration JSON under `$EVIDENCE`. Store the scenario-specific proof under `$EVIDENCE/<scenario-slug>/`.

| Artifact | Required evidence |
| --- | --- |
| `manifest-resolved.json` / `configure.json` | Resolved problem ID, GPU arch, four distinct managed agents, per-role model pool selections, CCCC Group/Actor/binding identities, and preserved native-body snapshots. |
| `{lead,algo,kernel,profiler}-check.json` | Model pool key and successful fixture preflight for each role before preparation. |
| `doctor.json` / `delivery.json` | Healthy CUDA toolchain, verified CCCC provider, connected four-member group bindings, and active delivery settings. |
| `submitted-solution.cu` / `solution-diff.patch` | Exact `solution.cu` produced by the team and unified diff against the problem's starter baseline. |
| `independent-verify.json` / `ncu-summary.txt` | Runner-owned compile and execution of ONLY `submitted-solution.cu` against the untouched locked `driver.cu` with `-DEXTENDED_SHAPES=1`, proving untouched workspace files, input immutability, numerical accuracy on visible + extended shapes, solo L2-flushed CUDA-event speedup, and `ncu` Speed-of-Light metrics. |
| `cccc-history.json` / `participation-summary.json` | Native CCCC Group history proving all four actors actively participated, with message counts, multi-recipient sends, and threaded replies. |
| `transcript-{lead,algo,kernel,profiler}-*.jsonl` | Native Web agent transcripts with actual tool calls (`houmao-cccc`, `nvcc`, `ncu`/`nsys`, file edits). |
| `channel-audit.json` | Zero Houmao peer mail, CCCC Mail, or CCCC provider-admin tool calls across all four agents. |
| `stop.json` | Clean shutdown of all four agents and private tmux servers, revocation of all four grants, verified Group deletion, credential removal, and surviving evidence root. |

## Cleanup

Always stop run-owned resources and confirm surviving evidence:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" stop \
  --run-meta "$RUN_META" | tee "$EVIDENCE/stop.json"
find "$EVIDENCE" -type f | sort > "$EVIDENCE/evidence-check.txt"
```

`stop` disconnects all four receivers, stops only the four recorded agents and verified private tmux servers, revokes the four recorded grants, deletes and verifies absence of the run Group, deletes the four external credential files, and leaves `evidence/` untouched.

If an agent wedges and operator recovery is required, capture diagnostic evidence first, mark the scenario failed/blocked, and only then invoke:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cuda_coop_lab.py" recovery-post \
  --run-meta "$RUN_META" --role lead --confirm-operator-recovery \
  --subject "Operator recovery" --body "Stop current work and become ready for shutdown."
```

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `manifest.toml` | `--manifest tests/instructional/agent-cccc-cuda-coop/manifest.toml` | Problem catalog (`default_problem = "gdn_prefill"`, selectable `gdn_prefill` or `fused_moe`), CUDA tool config, delivery defaults, and four Web slots. |
| `helpers/cuda_coop_lab.py` | `pixi run python tests/instructional/agent-cccc-cuda-coop/helpers/cuda_coop_lab.py --help` | Manifest resolution, four-agent CCCC provisioning, CUDA workspace seeding, Doctor, delivery control, prompting, quiescence wait, independent locked-driver verification (`-DEXTENDED_SHAPES=1` + `ncu`), transcript/participation/channel audit, recovery, and cleanup. |
| `helpers/roles/{lead,algo,kernel,profiler}.md` | `fixture.py prepare --system-prompt-file ...` | Four specialized CUDA engineering roles enforcing CCCC-chat-only peer communication and clear workspace ownership. |
| `helpers/problems/gdn_prefill/` | Selected via `manifest.toml` (`gdn_prefill`, default) | Standalone pure-CUDA Gated Delta Net prefill problem (`kernel_api.cuh`, locked `driver.cu`, starter `solution_starter.cu`, `Makefile`, `design-brief.md`). |
| `helpers/problems/fused_moe/` | Selected via `manifest.toml` (`fused_moe`) | Standalone pure-CUDA Fused Top-K MoE SwiGLU block problem (`kernel_api.cuh`, locked `driver.cu`, starter `solution_starter.cu`, `Makefile`, `design-brief.md`). |

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [four-agent-cuda-coop.md](cases/four-agent-cuda-coop.md) | `multi-agent`, `web`, `cccc-chat`, `cuda`, `manifest` | Four agents collaborate exclusively over CCCC chat to analyze, implement, profile (`nvcc`/`ncu`), and optimize the default manifest problem (`gdn_prefill`) with independent locked-driver verification. |
| [manifest-problem-switch.md](cases/manifest-problem-switch.md) | `multi-agent`, `web`, `cccc-chat`, `cuda`, `manifest` | Selecting Problem 2 (`fused_moe`) through `manifest.toml` switches the seeded CUDA workspace, locked driver, and four-agent optimization workflow cleanly without harness edits. |
