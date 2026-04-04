# Real-Agent All-Lanes Auto

This guide walks the canonical four-lane unattended validation path by hand. Use it when you want to understand the exact sequence behind `run_demo.sh auto` and the `real-agent-all-lanes-auto` HTT case.

## Goal

Verify that one owned `houmao-server` can launch all four supported lanes, expose them on `/houmao/agents`, accept prompt requests through the transport-neutral request route, produce the tracked sanitized report contract, and stop cleanly.

## Steps

1. Choose a fresh output root.

```bash
export DEMO_OUTPUT_DIR=/tmp/houmao-server-agent-api-all-lanes-auto
rm -rf "$DEMO_OUTPUT_DIR"
```

Expected:

```text
The output root does not exist before startup.
```

2. Run the canonical unattended path.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto \
  --demo-output-dir "$DEMO_OUTPUT_DIR"
```

Expected:

```text
The command exits 0 after start, inspect, prompt, verify, and stop all complete.
```

3. Inspect the shared control artifacts.

```bash
jq '{selected_lanes, shared_routes, steps}' "$DEMO_OUTPUT_DIR/control/report.sanitized.json"
```

Look for:

- all four lane ids are present
- `shared_routes.listed_agent_count = 4`
- `shared_routes.missing_agent_count = 0`
- `steps.verify_complete = true`

Representative output:

```json
{
  "selected_lanes": [
    "claude-tui",
    "codex-tui",
    "claude-headless",
    "codex-headless"
  ],
  "shared_routes": {
    "expected_agent_count": 4,
    "history_limit": 20,
    "listed_agent_count": 4,
    "missing_agent_count": 0
  }
}
```

4. Check one TUI lane and one headless lane.

```bash
jq '.lanes["claude-tui"], .lanes["codex-headless"]' \
  "$DEMO_OUTPUT_DIR/control/report.sanitized.json"
```

Look for:

- TUI lanes report `detail_transport = "tui"`
- headless lanes report `detail_transport = "headless"`
- headless lanes report `headless_turn_status = "completed"`

5. Confirm the tracked snapshot matched.

```bash
cat "$DEMO_OUTPUT_DIR/control/verify_result.json"
```

Expected:

```json
{
  "ok": true,
  "snapshot_updated": false
}
```

6. If the run failed, inspect the preserved evidence instead of rerunning immediately.

Check:

- `$DEMO_OUTPUT_DIR/control/shared_routes.json`
- `$DEMO_OUTPUT_DIR/lanes/<lane-id>/launch.json`
- `$DEMO_OUTPUT_DIR/lanes/<lane-id>/prompt-verification.json`
- `$DEMO_OUTPUT_DIR/lanes/<lane-id>/headless-turns/<turn-id>/status.json`
- `$DEMO_OUTPUT_DIR/logs/server/`
