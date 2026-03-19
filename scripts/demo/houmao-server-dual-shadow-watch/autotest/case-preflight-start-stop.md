# Case: Preflight Start Stop

Purpose: quickly discover the first environment or lifecycle blocker without requiring manual interaction in the live agent TUIs.

Default output root:

```bash
tmp/demo/houmao-server-dual-shadow-watch/autotest/case-preflight-start-stop
```

Run:

```bash
scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh case-preflight-start-stop
```

Expected artifacts:

- `artifacts/preflight.json`
- `artifacts/start.json`
- `artifacts/inspect.json`
- `artifacts/stop.json`
- `result.json`

Pass signal:

- `result.json` contains `"status": "passed"`

Fail signal:

- the script exits non-zero
- `result.json` contains `"status": "failed"`

This case intentionally does not require manual `tmux attach`. It only proves that the demo can preflight, start, inspect, and stop through the supported `houmao-server + houmao-srv-ctrl` boundary.
