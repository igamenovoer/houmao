# Headless Mail Ping-Pong Gateway Demo Pack

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This pack demonstrates one specific managed-agent workflow:

> Start a demo-owned `houmao-server`, launch one headless Claude Code agent and one headless Codex agent, kick off a single mailbox thread, let later turns wake through gateway mail notifiers, and verify the resulting ten-message / eleven-turn contract from pack-local artifacts.

The pack is intentionally headless-first in v1. It does not try to cover TUI/TUI or mixed-mode parity here.

## Prerequisites

- `pixi`
- `git`
- `tmux`
- `claude`
- `codex`
- usable tool config and credential material under `tests/fixtures/agents/brains/cli-configs/` and `tests/fixtures/agents/brains/api-creds/`

Tracked fixture sources used by the pack:

- dummy project: `tests/fixtures/dummy-projects/mailbox-demo-python`
- Claude recipe: `tests/fixtures/agents/brains/brain-recipes/claude/mail-ping-pong-initiator-default.yaml`
- Codex recipe: `tests/fixtures/agents/brains/brain-recipes/codex/mail-ping-pong-responder-default.yaml`
- initiator role: `tests/fixtures/agents/roles/mail-ping-pong-initiator`
- responder role: `tests/fixtures/agents/roles/mail-ping-pong-responder`

## Command Surface

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh \
  [auto|start|kickoff|wait|pause|continue|inspect|verify|stop] \
  [--demo-output-dir <path>] \
  [--parameters <path>] \
  [--timeout-seconds <seconds>] \
  [--poll-interval-seconds <seconds>] \
  [--expected-report <path>] \
  [--snapshot]
```

Commands:

- `auto`: `start -> kickoff -> wait -> verify`
- `start`: provision the output root, copy the tracked dummy projects, start the demo-owned `houmao-server`, build both tracked brains, launch both managed headless agents, attach both gateways, and enable both mail notifiers
- `kickoff`: submit the single direct request to the initiator through `POST /houmao/agents/{agent_ref}/requests`
- `wait`: poll bounded progress until the fixed-round conversation completes or times out
- `pause`: disable both gateway mail notifiers
- `continue`: re-enable both gateway mail notifiers
- `inspect`: refresh `control/inspect.json`, `control/conversation_events.jsonl`, and the current report snapshots
- `verify`: rebuild the report artifacts and compare `report.sanitized.json` with `expected_report/report.json`
- `stop`: disable notifiers, stop both managed agents, stop the demo-owned server, and preserve all run artifacts

Examples:

```bash
# One-shot happy path using the pack-local outputs/ root.
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh

# Stepwise walkthrough against a reusable output root.
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh start --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh kickoff --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh wait --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh inspect --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh verify --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh stop --demo-output-dir scripts/demo/mail-ping-pong-gateway-demo-pack/outputs-stepwise
```

If you override `--demo-output-dir`, keep using the same path for the rest of that run. The persisted state file under that root is the resumable source of truth.

## Kickoff And Thread Contract

The pack sends only one direct operator request.

`kickoff` generates one run-specific thread key such as `mail-ping-pong-20260323T120000Z-abcdef` and asks the initiator to:

- send round 1 to the responder now
- use the tracked subject format `[{thread_key}] Round {round_index} ping-pong`
- include visible `Thread-Key`, `Round`, `Round-Limit`, `Sender-Role`, and `Next-Role` lines in every message
- keep later messages inside the same mailbox thread
- stop after the initiator wakes to read reply 5

That contract yields:

- `10` total messages for the default round limit of `5`
- `11` completed turns
- `1` logical thread for the whole run

The final extra turn matters. The initiator must wake one last time to read round-5 reply mail and decide not to send round 6.

## Bounded Wait Behavior

`wait` reads the persisted `wait_defaults` from `inputs/demo_parameters.json` unless you override them on the command line.

Each poll refreshes:

- `control/conversation_events.jsonl`
- `control/inspect.json`
- `control/report.json`
- `control/report.sanitized.json`

Visible progress is reported as message count, completed-turn count, and unread counts. On timeout, `wait` exits non-zero, preserves the incomplete artifacts, and records the explicit failure reason in `report.json`.

## Output Ownership

All Houmao-generated state for a run lives under the selected output root. The default root is `scripts/demo/mail-ping-pong-gateway-demo-pack/outputs/`.

```text
<output-root>/
├── control/
│   ├── demo_state.json
│   ├── kickoff_request.json
│   ├── inspect.json
│   ├── conversation_events.jsonl
│   ├── report.json
│   └── report.sanitized.json
├── server/
│   ├── home/
│   ├── logs/
│   └── runtime/
├── runtime/
├── registry/
├── mailbox/
├── jobs/
├── projects/
│   ├── initiator/
│   └── responder/
└── monitor/
```

The pack exports these redirects before starting the demo-owned server:

- `AGENTSYS_GLOBAL_RUNTIME_DIR=<output-root>/runtime`
- `AGENTSYS_GLOBAL_REGISTRY_DIR=<output-root>/registry`
- `AGENTSYS_GLOBAL_MAILBOX_DIR=<output-root>/mailbox`
- `AGENTSYS_LOCAL_JOBS_DIR=<output-root>/jobs`

If a file was generated by this demo run, it should be somewhere under that output root.

## Verification

`verify` compares `control/report.sanitized.json` against `expected_report/report.json`.

The stable report contract checks:

- one thread
- ten messages
- eleven completed turns
- zero unread mail at the end
- notifier enqueue evidence for both roles
- exactly one direct kickoff request, with later progress attributed to gateway wake-up behavior rather than repeated operator prompts

Maintainers can refresh the tracked snapshot with:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh verify --snapshot
```

## Coverage Posture

V1 regression coverage for this pack is pytest-based only. There is no pack-local live-agent `autotest/` harness yet.

The current automated coverage lives in `tests/unit/demo/test_mail_ping_pong_gateway_demo_pack.py` and focuses on:

- startup defaults and `outputs/` containment
- persisted-state reuse
- successful report generation plus sanitization
- pause / continue notifier control
- timeout / incomplete-run diagnostics
