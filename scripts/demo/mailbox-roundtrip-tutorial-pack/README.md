# Mailbox Roundtrip Tutorial Pack

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This pack answers one maintainer-friendly question:

> How do I provision a demo-owned project worktree, launch two CAO-backed mailbox sessions, run the roundtrip, verify the sanitized report contract, and automate regression scenarios from the pack directory itself?

The pack now exposes two automation layers:

- `run_demo.sh` for the operator and stepwise maintainer command surface.
- `scripts/run_automation_scenarios.py` for named maintainer regression scenarios that archive machine-readable results under one automation root.

## Prerequisites

- `pixi` is installed and `pixi install` has been run at least once.
- `tmux` is installed and on `PATH`.
- The tracked Claude Code and Codex credential profiles selected by the demo blueprints are available under `tests/fixtures/agents/brains/api-creds/`.
- You are running from this repository checkout or from a valid git worktree of it.

The default verified path is still launcher-managed loopback CAO. When `CAO_BASE_URL` points at a supported loopback URL such as `http://localhost:9889`, the helper writes a demo-local launcher config under `<demo-output-dir>/cao/`, starts or reuses CAO there, derives the matching `--cao-profile-store`, and only stops that CAO later if the current demo run started it.

If `CAO_BASE_URL` points at an external CAO, the default automation path still exits with `SKIP:` guidance instead of guessing ownership or profile-store state.

## Command Surface

The pack wrapper now supports explicit commands:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh [auto|start|roundtrip|verify|stop] \
  [--demo-output-dir <path>] \
  [--jobs-dir <path>] \
  [--parameters <path>] \
  [--expected-report <path>] \
  [--cao-parsing-mode <shadow_only>] \
  [--snapshot-report]
```

For this mailbox roundtrip workflow, the pack uses `shadow_only` for both Claude and Codex. `cao_only` does not satisfy this pack's contract and is rejected by the pack-local scripts.

Commands:

- `auto`: start, roundtrip, verify, then stop. This remains the default command when no explicit command is supplied.
- `start`: provision the demo root, validate or create `<demo-output-dir>/project`, start both mailbox sessions, and persist reusable demo state.
- `roundtrip`: reuse the existing demo root and run `mail send -> mail check -> mail reply -> mail check`.
- `verify`: rebuild `report.json`, refresh `report.sanitized.json`, compare against `expected_report/report.json`, and optionally refresh the tracked snapshot with `--snapshot-report`.
- `stop`: stop demo-owned live sessions and any demo-managed CAO started by the current run.

Examples:

```bash
# One-shot operator path. This recreates the pack-local outputs/ root.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh

# Stepwise maintainer path against one reusable output root.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh start --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh roundtrip --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh verify --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh stop --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise

# Snapshot refresh from sanitized content only.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh verify \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise \
  --snapshot-report
```

## Demo Output Layout

The canonical default output root is `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/`. Full runs recreate that directory from scratch. Stepwise commands still reuse one selected output root for the same run.

The pack now separates maintainer-facing outputs from generated orchestration state:

```text
<output-root>/
├── mailbox/                    # canonical filesystem mailbox root
├── chats.jsonl                 # append-only semantic chat log for the tutorial exchange
├── inputs/                     # copied tracked inputs for the selected run
├── control/                    # helper-owned generated JSON artifacts
│   ├── demo_state.json
│   ├── cao_start.json
│   ├── sender_build.json
│   ├── receiver_build.json
│   ├── sender_start.json
│   ├── receiver_start.json
│   ├── mail_send.json
│   ├── receiver_check.json
│   ├── mail_reply.json
│   ├── sender_check.json
│   ├── report.json
│   ├── report.sanitized.json
│   ├── verify_result.json
│   ├── sender_stop.json        # emitted by explicit `stop` or successful `auto`
│   ├── receiver_stop.json
│   ├── stop_result.json
│   └── cleanup_*.json          # emitted when cleanup runs after failure or interruption
├── cao/                        # demo-local CAO launcher config and runtime artifacts
├── project/                    # git worktree used as the agents' workdir
├── runtime/                    # build-brain outputs and session manifests
```

Notes:

- Relative `--demo-output-dir` and `--jobs-dir` values resolve from the repository root.
- `--parameters` and `--expected-report` let maintainers swap in test-owned fixtures without editing the tracked pack inputs or snapshot.
- Fresh automatic `start` runs persist `shadow_only` in `<output-root>/control/demo_state.json`, and later `roundtrip` and `stop` commands reuse that persisted mode for the same demo root unless an explicit `shadow_only` override is supplied again.
- Demo roots that still persist `cao_only` are stale for this pack and should be discarded and recreated so the workflow restarts in `shadow_only`.
- When `--jobs-dir` is omitted, per-session jobs stay under `<demo-output-dir>/project/.houmao/jobs/<session-id>/`.
- Full runs refresh `<output-root>/` between runs, but a valid existing `<demo-output-dir>/project` worktree is preserved and reused.
- If `<demo-output-dir>/project` already exists but is not a valid git worktree of this repository, the automation fails before any live runtime work starts.
- The pack-local `.gitignore` ignores `outputs/` because that tree is disposable generated state.

## Live Automatic Coverage

The pack also has a dedicated live integration target that exercises the real direct-session mail path without using gateway transport or fake mailbox injection:

```bash
pixi run pytest tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py
```

That test:

- provisions a fresh temp-root `<demo-output-dir>` plus an isolated `AGENTSYS_GLOBAL_REGISTRY_DIR`
- starts a test-owned loopback CAO on a picked free port
- runs `run_demo.sh start -> roundtrip -> verify -> stop` against two real runtime sessions, with both agents using `shadow_only`
- treats Codex shadow parsing as the supported receiver path instead of a fallback or downgrade target
- asserts that `<demo-output-dir>/mailbox/mailboxes/<sender-address>/` and `<demo-output-dir>/mailbox/mailboxes/<receiver-address>/` both exist after `stop`
- opens the canonical send and reply Markdown documents under `<demo-output-dir>/mailbox/messages/`
- verifies that `<demo-output-dir>/chats.jsonl` records the semantic send and reply events without relying on CAO transcript scraping
- confirms the sanitized report still excludes the raw message bodies and raw chat content even though the canonical mailbox Markdown and `chats.jsonl` remain readable on disk

The existing `scripts/run_automation_scenarios.py` coverage remains the fast hermetic regression layer. It is not the only automatic mailbox check anymore; the live pytest target is the direct-codepath gate.

## Scenario Automation

The maintainer scenario runner lives inside the pack:

```bash
pixi run python scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/run_automation_scenarios.py \
  --automation-root tmp/demo/mailbox-automation
```

Select individual scenarios with repeated `--scenario` flags:

```bash
pixi run python scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/run_automation_scenarios.py \
  --automation-root tmp/demo/mailbox-automation \
  --scenario auto-implicit-jobs-dir \
  --scenario stepwise-start-roundtrip-verify-stop \
  --scenario partial-failure-cleanup
```

Current built-in scenarios:

- `auto-implicit-jobs-dir`
- `auto-explicit-jobs-dir`
- `stepwise-start-roundtrip-verify-stop`
- `rerun-valid-project-reuse`
- `incompatible-project-dir`
- `verify-snapshot-refresh`
- `cleanup-ownership-reused-managed-cao`
- `partial-failure-cleanup`
- `interrupted-run-cleanup`

Scenario outputs are written under the selected automation root:

```text
<automation-root>/
├── suite-summary.json
└── <scenario-id>/
    ├── commands/
    │   ├── 01-*.stdout.txt
    │   └── 01-*.stderr.txt
    ├── demo/                  # the per-scenario demo-output-dir when the scenario uses one
    └── scenario-result.json
```

`suite-summary.json` and each `scenario-result.json` are machine-readable and designed for both maintainers and integration tests.

## Verification Contract

`verify` and `auto` both build `<output-root>/control/report.json`, sanitize the result to `<output-root>/control/report.sanitized.json`, and compare only the sanitized content against `expected_report/report.json`.

The sanitized contract still masks path-, timestamp-, mailbox-, chat-log-, and request-dependent values. Stepwise verification uses the same contract as the one-shot `auto` flow, so maintainers can compare or refresh the snapshot after either path without needing a second unrelated run.

## Manual Realm-Controller Walkthrough

The pack still mirrors the same underlying runtime flow:

1. Start or reuse demo-local CAO.
2. Build sender and receiver brains.
3. Start both sessions against `<demo-output-dir>/project` and `<demo-output-dir>/mailbox`.
4. Send the initial message, check it from the receiver, reply with helper-generated content derived from the tracked reply instructions, and check the reply from the sender.
5. Append the semantic tutorial exchange to `<demo-output-dir>/chats.jsonl`.
6. Build and sanitize the report.
7. Stop the demo-owned resources.

The wrapper and scenario runner are just pack-owned automation layers around that sequence so maintainers do not need a separate test-only harness.
