# Houmao-Server Agent API Demo Pack

This pack answers one concrete question: how do you validate the direct `houmao-server` managed-agent API across Claude/Codex and TUI/headless lanes without using `tests/manual/` as the canonical operator surface?

Success looks like this:

- one owned `houmao-server` starts under a demo-owned output root
- the selected lanes become visible through `/houmao/agents`
- prompt submission succeeds through `POST /houmao/agents/{agent_ref}/requests`
- `verify` writes `report.json` and `report.sanitized.json`
- the sanitized report matches [`expected_report/report.json`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/expected_report/report.json)

## Prerequisites

- `pixi`
- `git`
- `tmux`
- `claude` for Claude lanes
- `codex` for Codex lanes
- live credential material under the pack-owned `agents/brains/api-creds/...` tree

The pack is self-contained for non-secret launch inputs. It uses:

- tracked native selectors under [`agents/`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/agents)
- tracked prompts and the copied project template under [`inputs/`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/inputs)
- generated run state under `scripts/demo/houmao-server-agent-api-demo-pack/outputs/`

## Implementation Idea

1. Run a fail-fast preflight against tools, credentials, selector assets, and output-root posture.
2. Start one isolated `houmao-server` and inject the pack-owned `AGENTSYS_AGENT_DEF_DIR`.
3. Provision the selected lanes directly through the public server API.
4. Inspect `/houmao/agents`, `/state`, `/state/detail`, and `/history`.
5. Submit prompts, optionally submit interrupts, and capture follow-up state.
6. Build a sanitized verification report and compare it to the tracked expected report.
7. Stop all managed agents through `/houmao/agents/{agent_ref}/stop` and then stop the owned server.

## Critical Inputs

The canonical prompt fixture is small and tracked:

```text
Reply with one short sentence confirming that the houmao-server agent API demo-pack prompt was received and handled successfully.
```

The interrupt-focused prompt fixture is also tracked and intentionally long-running:

```text
Work deliberately and produce a detailed numbered checklist with at least twenty items describing how you would inspect the copied dummy project before making any change. Do not summarize early.
```

The canonical all-lanes expected report is sanitized to remove absolute paths, timestamps, ids, and prompt text. The most important fields are:

```json
{
  "active": true,
  "pack": "houmao-server-agent-api-demo-pack",
  "selected_lanes": [
    "claude-tui",
    "codex-tui",
    "claude-headless",
    "codex-headless"
  ],
  "shared_routes": {
    "expected_agent_count": 4,
    "listed_agent_count": 4,
    "missing_agent_count": 0
  }
}
```

## REST Shape

The pack validates the direct server boundary itself. These are the important routes:

```bash
# list managed agents
curl -sS "$API_BASE_URL/houmao/agents"

# inspect one managed agent
curl -sS "$API_BASE_URL/houmao/agents/$AGENT_REF/state/detail"
curl -sS "$API_BASE_URL/houmao/agents/$AGENT_REF/history?limit=20"

# submit one prompt
curl -sS -X POST "$API_BASE_URL/houmao/agents/$AGENT_REF/requests" \
  -H 'content-type: application/json' \
  -d '{
    "request_kind": "submit_prompt",
    "prompt": "Please reply with one short sentence confirming this demo-pack prompt."
  }'

# submit one interrupt
curl -sS -X POST "$API_BASE_URL/houmao/agents/$AGENT_REF/requests" \
  -H 'content-type: application/json' \
  -d '{"request_kind": "interrupt"}'
```

The shell wrapper exists for convenience, but the workflow is intentionally stepwise and explicit.

## Run And Verify

### 1. Run a preflight-only pass

```bash
scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh \
  --case real-agent-preflight \
  --demo-output-dir /tmp/houmao-server-agent-api-preflight
```

Expected result:

```text
case: real-agent-preflight
demo_output_dir: /tmp/houmao-server-agent-api-preflight
expected_report: .../scripts/demo/houmao-server-agent-api-demo-pack/expected_report/report.json
```

The preflight JSON lands at:

- `/tmp/houmao-server-agent-api-preflight/control/autotest/case-real-agent-preflight.preflight.json`

### 2. Run the canonical unattended path

This is the same flow the `real-agent-all-lanes-auto` HTT case drives:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto \
  --demo-output-dir /tmp/houmao-server-agent-api-auto
```

That command performs:

1. `start`
2. `inspect`
3. `prompt`
4. `verify`
5. `stop`

Key success artifacts:

- `/tmp/houmao-server-agent-api-auto/control/demo_state.json`
- `/tmp/houmao-server-agent-api-auto/control/shared_routes.json`
- `/tmp/houmao-server-agent-api-auto/control/report.json`
- `/tmp/houmao-server-agent-api-auto/control/report.sanitized.json`
- `/tmp/houmao-server-agent-api-auto/control/verify_result.json`
- `/tmp/houmao-server-agent-api-auto/control/stop_result.json`

Representative verification output:

```json
{
  "ok": true,
  "snapshot_updated": false
}
```

### 3. Run the same workflow stepwise

Start only the selected lanes:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh start \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise \
  --lane claude-tui \
  --lane codex-headless
```

Inspect the same persisted run:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh inspect \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise \
  --with-dialog-tail 400
```

Submit the canonical prompt:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh prompt \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise
```

Submit an interrupt:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh interrupt \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise
```

Verify and stop:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh verify \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh stop \
  --demo-output-dir /tmp/houmao-server-agent-api-stepwise
```

### 4. Compare current output to the tracked expected report

```bash
diff -u \
  scripts/demo/houmao-server-agent-api-demo-pack/expected_report/report.json \
  /tmp/houmao-server-agent-api-auto/control/report.sanitized.json
```

### 5. Refresh the tracked expected report intentionally

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh verify \
  --demo-output-dir /tmp/houmao-server-agent-api-auto \
  --snapshot-report
```

This updates only the sanitized snapshot under [`expected_report/report.json`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/expected_report/report.json).

## HTT Cases

Use the standalone harness when you want named real-agent cases with preserved phase logs:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh \
  --case real-agent-all-lanes-auto \
  --demo-output-dir /tmp/houmao-server-agent-api-autotest
```

Supported cases:

- `real-agent-preflight`
- `real-agent-all-lanes-auto`
- `real-agent-interrupt-recovery`

The harness preserves:

- machine-readable results under `<demo-output-dir>/control/autotest/`
- phase logs under `<demo-output-dir>/logs/autotest/<case-id>/`

## Troubleshooting

- If preflight fails immediately, inspect `control/autotest/case-real-agent-preflight.preflight.json` first.
- If startup succeeds but a lane never appears on `/houmao/agents`, inspect `control/shared_routes.json` and `lanes/<lane-id>/launch.json`.
- If prompt or interrupt validation fails, inspect `lanes/<lane-id>/prompt-verification.json` or `lanes/<lane-id>/interrupt-verification.json`.
- If cleanup fails, inspect `control/stop_result.json` and `logs/server/`.

## Appendix

| Name | Value | Explanation |
| --- | --- | --- |
| `agent_profile` | `server-api-smoke` | Native selector resolved from the pack-owned `agents/` tree. |
| Default lanes | `claude-tui`, `codex-tui`, `claude-headless`, `codex-headless` | Canonical aggregate validation set. |
| History limit | `20` | Default `/history` bound used during inspect and interrupt evidence capture. |
| Default output root | `scripts/demo/houmao-server-agent-api-demo-pack/outputs/` | Pack-local generated run and autotest artifact root. |
| Snapshot path | `expected_report/report.json` | Sanitized golden report used by `verify`. |

Tracked input files:

- [`inputs/prompt.txt`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/inputs/prompt.txt)
- [`inputs/interrupt_prompt.txt`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/inputs/interrupt_prompt.txt)
- [`inputs/demo_parameters.json`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/inputs/demo_parameters.json)
- [`inputs/project-template/README.md`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/inputs/project-template/README.md)
- [`agents/README.md`](/data1/huangzhe/code/houmao/scripts/demo/houmao-server-agent-api-demo-pack/agents/README.md)

Generated output files:

- `<demo-output-dir>/control/demo_state.json`
- `<demo-output-dir>/control/shared_routes.json`
- `<demo-output-dir>/control/report.json`
- `<demo-output-dir>/control/report.sanitized.json`
- `<demo-output-dir>/control/verify_result.json`
- `<demo-output-dir>/control/stop_result.json`
- `<demo-output-dir>/logs/autotest/<case-id>/*.stdout.txt`
- `<demo-output-dir>/logs/autotest/<case-id>/*.stderr.txt`
