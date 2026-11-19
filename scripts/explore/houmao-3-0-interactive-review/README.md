# Houmao 3.0 Interactive Review Campaign Harness

Executable diagnostic tooling and isolation wrappers for the debug campaign at [2026-11-18 Houmao 3.0 Interactive Review](../../../context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/).

All tooling in this directory is temporary campaign support software. Diagnostic execution does not modify production code under `src/houmao/` or `packages/houmao-cccc/`, committed tests under `tests/`, or specifications under `openspec/`. The 2026-11-19 checkout-`tmp` storage-policy fix was separately and explicitly requested by the operator outside this read-only diagnostic boundary.

**Release boundary:** `iter1_dsh.py` and the workflow below are historical RC1/RC2 tooling. Houmao RC3 replaces `--headless` and `--no-headless` with `--mode`, separates native one-shot headless execution from persistent ACP service mode, and requires fresh runtime schemas. Do not use this helper to create profiles, launch, stop, or relaunch RC3 agents. Follow [Iteration 2](../../../context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md) and use the maintained `scripts/agents/test-fixtures/fixture.py` workflow for RC3.

## RC3 Launch Materials

Canonical source inputs are `scripts/agents/test-fixtures/fixture.py`, the descriptors under `tests/fixtures/agent-launch/`, the campaign role `tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt`, and the explicitly selected DSH executable at `tmp/dsh/npm-runtime/node_modules/.bin/dsh`. See [Iteration 2](../../../context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md) for the complete prepare command.

All generated RC3 inputs and fixture runs are stored physically under the Git-ignored `tmp/houmao-30-iter2-rc3/` directory. Each run contains `run.json`, `assets/`, `home/`, `workdir/`, a private environment file, and an isolated tmux shim. The fixture and gateway storage policies allow purpose-specific checkout `tmp/` run roots while preserving other private-path checks. The current preparation checkpoint is recorded in [this evidence](../../../context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/evidences/2026-11-19-rc3-iteration2-g0-and-h1-preparation.md).

## Safety and Isolation Rules

Every script under this directory obeys three hard environment boundaries:

1. **Isolated tmux server only**: All tmux wrappers clear inherited `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR` and bind a PATH shim forcing `-L houmao-30-iter1` (or `--tmux-server <name>`). Teardown only stops that explicit `-L` server and verifies default tmux sessions (`mao-*`, `rsi-*`) remain unchanged.
2. **Isolated Houmao project and gateway access roots**: Historical RC1/RC2 project overlays, launch profiles, workdirs, tmux shims, and `HOUMAO_GLOBAL_*` roots (`registry/`, `runtime/`, `mailbox/`) live inside the gitignored repository scratch tree (`tmp/houmao-30-iter1/` by default; system `/tmp` is not used). Before the 2026-11-19 storage-policy fix, `houmao.gateway._access_storage` rejected every checkout path, so historical generated Ed25519 admin keys, `gateway-admin-seed.json`, and `XDG_CONFIG_HOME` (`gateway-access/`) live outside the checkout under `~/.local/state/houmao-30-iter1/` (`0700`/`0600`). RC3 Iteration 2 materials instead use the physical `tmp/houmao-30-iter2-rc3/` hierarchy described above.
3. **No credential echo**: `.env` keys are read into memory solely to check presence or provision an external arm directory. Secret tokens, cookies, and API keys are never printed or written into campaign Markdown logs.

## Directory Layout

| Path | Purpose |
| --- | --- |
| `common.py` | Shared tmux isolation, clean environment builder, HTTP model/usage probes, and `houmao-mgr` runner |
| `iter1_dsh.py` | Historical RC1/RC2 stepwise runner for Iteration 1 (`g0`, `a0`, `setup-arm`, `launch`, `send`, `interrupt`, `watch`, `stop`, `teardown`); not valid for RC3 profile or lifecycle operations |
| `attach.sh` | Shortcut script to attach to the isolated `tmp/houmao-30-iter1/` tmux session (`attach.sh [b1\|b2\|a1\|a2]`) |
| `README.md` | Overview and operator usage reference |

## Historical RC1/RC2 Quick Start: Gate G0 Offline Self-Test

Run the offline Gate G0 check to verify isolated tmux execution, DSH version policy (`>=0.2.2rc1`, release and `rc` only), host `dsh` binary recognition, `.env` variable presence, and default tmux server safety:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py g0 --self-test
```

To also probe an active self-hosted Qwen 3.8 endpoint during G0:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py g0 --qwen-base-url http://127.0.0.1:14888/v1
```

## Historical Iteration 1 RC1/RC2 Stepwise Workflow

Drive each Iteration 1 arm step by step so a human reviewer can attach to `tmux -L houmao-30-iter1`, inspect native Web UIs, and observe gateway logs between turns:

```bash
# Arm A0: cold setup and guardrail probe (no LLM calls)
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py a0

# Generate Ed25519 admin keypairs and validated gateway-admin-seed.json
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py gen-admin-keys

# Prepare Qwen 3.8 DSH launch profiles (B1 headless ACP, B2 interactive Web) with admin seed
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py setup-arm \
  --arm b1 --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --reasoning '{"0":"off","1":"low","2":"medium","3":"high"}' \
  --profile-name dsh-qwen38-acp --admin-seed ~/.local/state/houmao-30-iter1/keys/gateway-admin-seed.json

# Arm A1 (dsh_acp) or A2 (dsh_web) on DeepSeek API (.env)
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py setup-arm --arm a1 --model deepseek-chat
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py launch --arm b1
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py send --arm b1 --prompt-id P1
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py watch --arm b1
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py stop --arm b1

# Gate G4 teardown (cleans only -L houmao-30-iter1)
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py teardown --kill-server
```
