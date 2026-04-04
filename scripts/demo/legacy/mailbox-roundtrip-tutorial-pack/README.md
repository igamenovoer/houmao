# Mailbox Roundtrip Tutorial Pack

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This pack answers one maintainer-friendly question:

> How do I provision a demo-owned dummy project, launch two CAO-backed mailbox sessions, run the roundtrip, inspect slow turns, verify the sanitized report contract, and automate regression scenarios from the pack directory itself?

The pack now exposes three automation layers:

- `run_demo.sh` for the operator and stepwise maintainer command surface.
- `autotest/run_autotest.sh` for canonical opt-in real-agent HTT cases.
- `scripts/run_automation_scenarios.py` for named maintainer regression scenarios that archive machine-readable results under one automation root.

## Prerequisites

- `pixi` is installed and `pixi install` has been run at least once.
- `tmux` is installed and on `PATH`.
- The tracked Claude Code and Codex credential profiles selected by the demo blueprints are available under `tests/fixtures/agents/brains/api-creds/`.
- You are running from this repository checkout so the pack can copy the tracked dummy-project fixture into the selected demo output directory.

The default verified path is still launcher-managed loopback CAO. When `CAO_BASE_URL` points at a supported loopback URL such as `http://localhost:9889`, the helper writes a demo-local launcher config under `<demo-output-dir>/cao/`, starts or reuses CAO there, derives the matching `--cao-profile-store`, and only stops that CAO later if the current demo run started it.

If `CAO_BASE_URL` points at an external CAO, the default `run_demo.sh` path still exits with `SKIP:` guidance instead of guessing ownership or profile-store state. The real-agent autotest harness is stricter: it fails preflight instead of treating that mismatch as a soft skip.

## Command Surface

The pack exposes one deterministic tutorial wrapper plus one dedicated real-agent harness.

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh [auto|start|roundtrip|inspect|verify|stop] \
  [--demo-output-dir <path>] \
  [--jobs-dir <path>] \
  [--parameters <path>] \
  [--expected-report <path>] \
  [--cao-parsing-mode <shadow_only>] \
  [--agent <sender|receiver>] \
  [--json] \
  [--with-output-text <chars>] \
  [--snapshot-report]
```

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh \
  [--case <real-agent-roundtrip|real-agent-preflight|real-agent-mailbox-persistence>] \
  [--demo-output-dir <path>] \
  [--parameters <path>] \
  [--expected-report <path>] \
  [--jobs-dir <path>] \
  [--registry-dir <path>] \
  [--phase-timeout-seconds <seconds>]
```

For this mailbox roundtrip workflow, the pack uses `shadow_only` for both Claude and Codex. `cao_only` does not satisfy this pack's contract and is rejected by the pack-local scripts. `run_demo.sh` stays focused on the tutorial/operator flow; `autotest/run_autotest.sh` owns case selection, fail-fast real-agent preflight, timeout-bounded phase execution, and machine-readable HTT evidence.

Commands:

- `auto`: start, roundtrip, verify, then stop. This remains the default command when no explicit command is supplied.
- `start`: provision the demo root, copy the tracked dummy-project fixture into `<demo-output-dir>/project`, initialize a fresh pinned-metadata git repo there, start both mailbox sessions, and persist reusable demo state.
- `roundtrip`: reuse the existing demo root and run `mail send -> mail check -> mail reply -> mail check`.
- `inspect`: show persisted tmux/log coordinates for `sender` or `receiver`, plus live CAO `tool_state` and optional projected output tail when available.
- `verify`: rebuild `report.json`, refresh `report.sanitized.json`, compare against `expected_report/report.json`, and optionally refresh the tracked snapshot with `--snapshot-report`.
- `stop`: stop demo-owned live sessions and any demo-managed CAO started by the current run.

Real-agent autotest cases:

- `real-agent-preflight`: fail fast on missing tools, missing credential/config material, unsafe output-root reuse, unsupported CAO ownership, or non-isolated runtime roots.
- `real-agent-roundtrip`: run `start -> roundtrip -> verify -> stop` through the pack wrapper and then reopen the mailbox artifacts from disk.
- `real-agent-mailbox-persistence`: run the same live roundtrip flow and fail if the sender/receiver mailbox directories or canonical send/reply Markdown files are unreadable after stop.

Examples:

```bash
# One-shot operator path. This recreates the pack-local outputs/ root.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh

# Stepwise maintainer path against one reusable output root.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh start --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh inspect --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise --agent sender
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh inspect --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise --agent receiver --json --with-output-text 400
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh roundtrip --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh verify --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh stop --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise

# Snapshot refresh from sanitized content only.
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh verify \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs-stepwise \
  --snapshot-report

# Canonical real-agent HTT path with an explicit reusable output root.
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh \
  --case real-agent-roundtrip \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/live-roundtrip
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
│   ├── cleanup_*.json          # emitted when cleanup runs after failure or interruption
│   └── testplans/              # real-agent autotest results and per-phase logs
├── cao/                        # demo-local CAO launcher config and runtime artifacts
├── project/                    # copied dummy-project fixture initialized as a fresh git repo
├── runtime/                    # build-brain outputs and session manifests
```

Notes:

- Relative `--demo-output-dir` and `--jobs-dir` values resolve from the repository root.
- `--parameters` and `--expected-report` let maintainers swap in test-owned fixtures without editing the tracked pack inputs or snapshot.
- Fresh automatic `start` runs persist `shadow_only` in `<output-root>/control/demo_state.json`, and later `roundtrip` and `stop` commands reuse that persisted mode for the same demo root unless an explicit `shadow_only` override is supplied again.
- Demo roots that still persist `cao_only` are stale for this pack and should be discarded and recreated so the workflow restarts in `shadow_only`.
- When `--jobs-dir` is omitted, per-session jobs stay under `<demo-output-dir>/project/.houmao/jobs/<session-id>/`.
- `autotest/run_autotest.sh` sets demo-local `--jobs-dir` and `AGENTSYS_GLOBAL_REGISTRY_DIR` roots under `<demo-output-dir>/runtime/` so the real-agent HTT path does not lean on unrelated ambient state.
- The default tracked fixture is `tests/fixtures/dummy-projects/mailbox-demo-python`.
- The default tracked blueprints are `blueprints/mailbox-demo-claude.yaml` and `blueprints/mailbox-demo-codex.yaml`.
- Fresh `start` runs copy the source-only dummy project into `<demo-output-dir>/project`, write `.houmao-demo-project.json`, initialize a new git repo, and create one pinned initial commit.
- Full reruns against the same stopped demo root re-provision that managed dummy project deterministically instead of preserving ad hoc edits inside `project/`.
- If `<demo-output-dir>/project` already exists before a stopped demo state is present, the automation fails before any live runtime work starts.
- The pack-local `.gitignore` ignores `outputs/` because that tree is disposable generated state.

## Autotest Directory

The implemented real-agent assets live under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/`:

- `run_autotest.sh`
- `case-real-agent-preflight.sh` plus `case-real-agent-preflight.md`
- `case-real-agent-roundtrip.sh` plus `case-real-agent-roundtrip.md`
- `case-real-agent-mailbox-persistence.sh` plus `case-real-agent-mailbox-persistence.md`
- `helpers/common.sh`

The `.md` files in `autotest/` are operator-facing companion docs for the shipped cases. They are not copies of the design-phase OpenSpec files under `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/`.

## Automatic Coverage

The pack has two deterministic automatic lanes:

- `pixi run pytest tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py`
- `pixi run python scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/run_automation_scenarios.py --automation-root <path>`

The live pytest target exercises the real direct-session mail path without using gateway transport or fake mailbox injection:

```bash
pixi run pytest tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py
```

That test:

- provisions a fresh temp-root `<demo-output-dir>` plus an isolated `AGENTSYS_GLOBAL_REGISTRY_DIR`
- starts a test-owned loopback CAO on a picked free port
- runs `run_demo.sh start -> inspect -> roundtrip -> verify -> stop` against two real runtime sessions, with both agents using `shadow_only`
- uses the tracked `mailbox-demo` role family and copied dummy-project fixture shape while replacing the external `claude` and `codex` binaries with deterministic test-owned stand-ins
- treats Codex shadow parsing as the supported receiver path instead of a fallback or downgrade target
- asserts that `<demo-output-dir>/mailbox/mailboxes/<sender-address>/` and `<demo-output-dir>/mailbox/mailboxes/<receiver-address>/` both exist after `stop`
- opens the canonical send and reply Markdown documents under `<demo-output-dir>/mailbox/messages/`
- verifies that `<demo-output-dir>/chats.jsonl` records the semantic send and reply events without relying on CAO transcript scraping
- confirms the sanitized report still excludes the raw message bodies and raw chat content even though the canonical mailbox Markdown and `chats.jsonl` remain readable on disk

The scenario runner remains the fast hermetic regression layer. Together, the scenario runner and live pytest target are deterministic automatic coverage; neither one claims to exercise the operator's real local Claude/Codex CLIs.

## Real-Agent Autotest

The canonical live-agent contract now lives under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh`.

When `--demo-output-dir` is omitted, the harness creates a timestamped case-owned output root under `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/`. Each successful or failed case writes machine-readable evidence under `<demo-output-dir>/control/testplans/` plus per-phase logs under `<demo-output-dir>/control/testplans/logs/`.

The companion case docs are:

- `autotest/case-real-agent-preflight.md`
- `autotest/case-real-agent-roundtrip.md`
- `autotest/case-real-agent-mailbox-persistence.md`

The harness prints stable `run_demo.sh inspect ...` commands after `start` so maintainers can inspect sender and receiver sessions while the live turns are in flight. It also records those inspect commands, the final mailbox directories, and the canonical send/reply Markdown paths in the case result JSON.

The compatibility boundary is explicit:

- `run_demo.sh`, the scenario runner, and the deterministic live pytest lane remain regression aids.
- `autotest/run_autotest.sh` is the only pack-owned path that claims to satisfy the real-agent live HTT contract.
- `tests/manual/manual_mailbox_roundtrip_real_agent_smoke.py` remains available as a convenience wrapper, but it now delegates directly to `autotest/run_autotest.sh` instead of defining a separate live-flow contract.

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
4. Use `run_demo.sh inspect --agent sender|receiver` whenever you need tmux attach, terminal-log tail, live `tool_state`, or best-effort projected output tail for one session.
5. Send the initial message, check it from the receiver, reply with helper-generated content derived from the tracked reply instructions, and check the reply from the sender.
6. Append the semantic tutorial exchange to `<demo-output-dir>/chats.jsonl`.
7. Build and sanitize the report.
8. Stop the demo-owned resources.

The wrapper and scenario runner are just pack-owned automation layers around that sequence so maintainers do not need a separate test-only harness.
