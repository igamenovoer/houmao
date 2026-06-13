# AG-UI Real Tmux Workbench Smoke

This opt-in smoke attaches the AG-UI workbench tmux tab to a real tmux session and records evidence for terminal repaint and resize debugging. It can validate the Bun-native tmux PTY backend when the workbench server is started with `bun run dev:bun`.

It expects an already-running workbench server and a real tmux session. To validate the Bun backend:

```bash
tmux new-session -d -s houmao-debug-attach-probe 'printf "tmux probe ready\n"; exec bash'

cd apps/ag-ui-workbench
bun run dev:bun --host 127.0.0.1 --port 5177
```

Then run the smoke from the repository root in another shell:

```bash
HMWB_WORKBENCH_URL=http://127.0.0.1:5177 \
HMWB_TMUX_SESSION=houmao-debug-attach-probe \
scripts/demo/ag-ui-real-tmux-workbench-smoke/run_smoke.sh
```

Evidence is written to `tmp/ag-ui-real-tmux-smoke-*` by default, or to `HMWB_REAL_TMUX_EVIDENCE_DIR` when set. The evidence includes screenshots before scroll, after scroll, after resize, plus `summary.json` with xterm data attributes, terminal host dimensions, rendered row count, and `tmux list-panes` size.
