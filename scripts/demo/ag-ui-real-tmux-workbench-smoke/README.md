# AG-UI Real Tmux Workbench Smoke

This opt-in smoke attaches the AG-UI workbench tmux tab to a real tmux session and records evidence for terminal repaint and resize debugging.

It expects an already-running workbench server and a real tmux session:

```bash
HMWB_WORKBENCH_URL=http://127.0.0.1:5177 \
HMWB_TMUX_SESSION=houmao-debug-attach-probe \
scripts/demo/ag-ui-real-tmux-workbench-smoke/run_smoke.sh
```

Evidence is written to `tmp/ag-ui-real-tmux-smoke-*` by default, or to `HMWB_REAL_TMUX_EVIDENCE_DIR` when set. The evidence includes screenshots before scroll, after scroll, after resize, plus `summary.json` with xterm data attributes, terminal host dimensions, rendered row count, and `tmux list-panes` size.
