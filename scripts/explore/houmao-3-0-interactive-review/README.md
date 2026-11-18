# Houmao 3.0 Interactive Review Campaign Harness

Executable diagnostic tooling and isolation wrappers for the debug campaign at [2026-11-18 Houmao 3.0 Interactive Review](../../../context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/).

All tooling in this directory is temporary campaign support software. Production code under `src/houmao/` and `packages/houmao-cccc/`, committed tests under `tests/`, and specifications under `openspec/` remain unmodified during campaign execution.

## Safety and Isolation Rules

Every script under this directory obeys three hard environment boundaries:

1. **Isolated tmux server only**: All tmux wrappers clear inherited `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR` and bind a PATH shim forcing `-L houmao-30-iter1` (or `--tmux-server <name>`). Teardown only stops that explicit `-L` server and verifies default tmux sessions (`mao-*`, `rsi-*`) remain unchanged.
2. **Isolated Houmao project and gateway access roots**: Campaign project overlays, launch profiles, workdirs, tmux shims, and `HOUMAO_GLOBAL_*` roots (`registry/`, `runtime/`, `mailbox/`) live inside the gitignored repository scratch tree (`tmp/houmao-30-iter1/` by default; system `/tmp` is not used). Because `houmao.gateway._access_storage` enforces `_reject_checkout()` against any ancestor directory containing `.git` (including gitignored subdirectories inside the repository), generated Ed25519 admin keys, `gateway-admin-seed.json`, and `XDG_CONFIG_HOME` (`gateway-access/`) live outside the checkout under `~/.local/state/houmao-30-iter1/` (`0700`/`0600`).
3. **No credential echo**: `.env` keys are read into memory solely to check presence or provision an external arm directory. Secret tokens, cookies, and API keys are never printed or written into campaign Markdown logs.

## Directory Layout

| Path | Purpose |
| --- | --- |
| `common.py` | Shared tmux isolation, clean environment builder, HTTP model/usage probes, and `houmao-mgr` runner |
| `iter1_dsh.py` | Stepwise interactive CLI runner for Iteration 1 (`g0`, `a0`, `setup-arm`, `launch`, `send`, `interrupt`, `watch`, `stop`, `teardown`) |
| `attach.sh` | Shortcut script to attach to the isolated `tmp/houmao-30-iter1/` tmux session (`attach.sh [b1\|b2\|a1\|a2]`) |
| `README.md` | Overview and operator usage reference |

## Quick Start: Gate G0 Offline Self-Test

Run the offline Gate G0 check to verify isolated tmux execution, DSH version policy (`>=0.2.2rc1`, release and `rc` only), host `dsh` binary recognition, `.env` variable presence, and default tmux server safety:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py g0 --self-test
```

To also probe an active self-hosted Qwen 3.8 endpoint during G0:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py g0 --qwen-base-url http://127.0.0.1:14888/v1
```

## Iteration 1 Stepwise Workflow

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
