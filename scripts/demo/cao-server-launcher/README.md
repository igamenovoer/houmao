# How Do I Validate `cao_server_launcher` End-to-End?
nDefault agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path`).


This tutorial pack answers one concrete question:

> "How can I run `status -> start -> status -> stop -> status` for the CAO
> launcher and verify the behavior with a reproducible, tracked report?"

Success means you can run the demo from a clean checkout, inspect each launcher
JSON payload, and confirm the run matches `expected_report/report.json`.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `cao-server` is on `PATH` (`command -v cao-server`).
- [ ] You are running from this repository checkout.

If a prerequisite is missing, the demo exits `0` with a `SKIP:` message instead
of mutating tracked files.

## Implementation Idea

1. Copy tracked inputs from `inputs/` into a fresh temp workspace.
2. Render a workspace-local launcher config from template placeholders.
3. Run launcher commands in order and capture JSON/exit codes for each step.
4. Build a raw report with payloads plus artifact-path checks.
5. Sanitize non-deterministic fields and compare against tracked expected output.

## Critical Example Code (Launcher CLI with Inline Comments)

```bash
# 1) Probe current health; exit code is 0 (healthy) or 2 (unhealthy).
pixi run python -m gig_agents.cao.tools.cao_server_launcher status \
  --config "$CONFIG_PATH" \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS" \
  >"$WORKSPACE_DIR/status_before_start.json" \
  2>"$WORKSPACE_DIR/status_before_start.err"

# 2) Start CAO server (or reuse an already healthy one).
pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
  --config "$CONFIG_PATH" \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS" \
  --poll-interval-seconds "$POLL_INTERVAL_SECONDS" \
  >"$WORKSPACE_DIR/start.json" \
  2>"$WORKSPACE_DIR/start.err"

# 3) Confirm health after start must be healthy (exit code 0).
pixi run python -m gig_agents.cao.tools.cao_server_launcher status \
  --config "$CONFIG_PATH" \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS" \
  >"$WORKSPACE_DIR/status_after_start.json" \
  2>"$WORKSPACE_DIR/status_after_start.err"

# 4) Stop pidfile-managed process for this runtime root.
pixi run python -m gig_agents.cao.tools.cao_server_launcher stop \
  --config "$CONFIG_PATH" \
  --grace-period-seconds "$GRACE_PERIOD_SECONDS" \
  --poll-interval-seconds "$POLL_INTERVAL_SECONDS" \
  >"$WORKSPACE_DIR/stop.json" \
  2>"$WORKSPACE_DIR/stop.err"

# 5) Probe health again after stop; may be 0 or 2 depending local state.
pixi run python -m gig_agents.cao.tools.cao_server_launcher status \
  --config "$CONFIG_PATH" \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS" \
  >"$WORKSPACE_DIR/status_after_stop.json" \
  2>"$WORKSPACE_DIR/status_after_stop.err"
```

## Critical Input Snippets

`inputs/demo_parameters.json`:

```json
{
  "base_url": "http://localhost:9889",
  "grace_period_seconds": 10.0,
  "poll_interval_seconds": 0.2,
  "proxy_policy": "clear",
  "startup_timeout_seconds": 15.0,
  "status_timeout_seconds": 3.0
}
```

`inputs/launcher_config.template.toml`:

```toml
base_url = "__BASE_URL__"
runtime_root = "__RUNTIME_ROOT__"
home_dir = "__HOME_DIR__"
proxy_policy = "__PROXY_POLICY__"
startup_timeout_seconds = __STARTUP_TIMEOUT_SECONDS__
```

## Critical Output Snippet

Sanitized contract shape written by verification tooling:

```json
{
  "demo": "cao-server-launcher",
  "flow": ["status", "start", "status", "stop", "status"],
  "checks": {
    "artifact_layout_matches": true,
    "launcher_result_exists_after_start": true,
    "post_start_status_healthy": true,
    "start_exit_code_is_zero": true,
    "stop_exit_code_is_zero": true
  },
  "start_mode": "<STARTED_NEW_OR_REUSED_EXISTING>",
  "stop_outcome": "<STOPPED_OR_ALREADY_STOPPED>"
}
```

## Run + Verify Walkthrough

1. Run the full demo wrapper.

   ```bash
   scripts/demo/cao-server-launcher/run_demo.sh
   ```

   Expected terminal lines:

   ```text
   [demo][cao-server-launcher] workspace: ...
   [demo][cao-server-launcher] status_before_start: exit=...
   [demo][cao-server-launcher] start: exit=0 ...
   [demo][cao-server-launcher] verification passed
   [demo][cao-server-launcher] demo complete
   ```

2. Inspect raw + sanitized output in the workspace printed by the script.

   ```bash
   ls -1 "$WORKSPACE_DIR" | rg 'report|status_|start|stop'
   ```

   Expected key files:

   ```text
   report.json
   report.sanitized.json
   status_before_start.json
   start.json
   status_after_start.json
   stop.json
   status_after_stop.json
   ```

3. Manually compare sanitized output to tracked expected report (optional, the
   wrapper already enforces this).

   ```bash
   diff -u \
     "$WORKSPACE_DIR/report.sanitized.json" \
     scripts/demo/cao-server-launcher/expected_report/report.json
   ```

   Expected output:

   ```text
   # no output means the files match
   ```

## Refresh Snapshot Contract

Use this only when launcher behavior changes intentionally:

```bash
scripts/demo/cao-server-launcher/run_demo.sh --snapshot-report
```

The command writes a sanitized payload into
`expected_report/report.json` and leaves other tracked files untouched.

## Troubleshooting

- `SKIP: pixi not found on PATH`
  - Install Pixi and retry.
- `SKIP: cao-server not found on PATH`
  - Install CAO CLI (`uv tool install cli-agent-orchestrator`) and retry.
- `SKIP: cao-server did not become healthy within startup timeout`
  - The local CAO runtime is unavailable in this environment; inspect
    `start.err` and launcher log files under the printed workspace path.
- `SKIP: port 9889 is already in use by another local process`
  - Stop the conflicting process or point the tutorial input to an available
    supported launcher base URL.
- `FAIL: unexpected exit code for start`
  - Inspect `start.err` and `start.json` in the printed workspace path.
- Persistent `HTTP 502` from `status` on localhost
  - Confirm your shell proxy settings allow local bypass; this demo auto-merges
    `NO_PROXY/no_proxy` with `localhost,127.0.0.1,::1`.
- `sanitized report mismatch`
  - Re-run in snapshot mode if the change is intentional; otherwise inspect
    raw launcher outputs for regressions.

## Appendix: Key Parameters

| Name | Value | Explanation |
|---|---|---|
| `base_url` | `http://localhost:9889` | CAO launcher target URL (supported local values only). |
| `NO_PROXY`/`no_proxy` | merged with `localhost,127.0.0.1,::1` | Prevents local launcher probes from being routed through external proxies. |
| `proxy_policy` | `clear` | Drops proxy env vars for launched CAO process while preserving loopback `NO_PROXY`. |
| `startup_timeout_seconds` | `15.0` | Max wait for health polling after `start`. |
| `status_timeout_seconds` | `3.0` | Timeout per `status` health request. |
| `poll_interval_seconds` | `0.2` | Poll interval used by `start` and `stop`. |
| `grace_period_seconds` | `10.0` | SIGTERM grace period before SIGKILL fallback in `stop`. |

## Appendix: File Inventory

Input files (tracked):

- `inputs/demo_parameters.json`
- `inputs/launcher_config.template.toml`

Expected output (tracked):

- `expected_report/report.json`

Scripts:

- `run_demo.sh`
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`

Generated workspace outputs (untracked):

- `status_before_start.json`, `status_before_start.err`, `status_before_start.exit_code`
- `start.json`, `start.err`, `start.exit_code`
- `status_after_start.json`, `status_after_start.err`, `status_after_start.exit_code`
- `stop.json`, `stop.err`, `stop.exit_code`
- `status_after_stop.json`, `status_after_stop.err`, `status_after_stop.exit_code`
- `report.json`
- `report.sanitized.json`
- `cao-server-launcher.toml`
