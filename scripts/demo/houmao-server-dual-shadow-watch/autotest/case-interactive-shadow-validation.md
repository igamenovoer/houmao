# Case: Interactive Shadow Validation

Purpose: run the real operator journey against the demo-owned `houmao-server`, then manually validate live parser and lifecycle transitions while interacting with both TUIs.

Default output root:

```bash
tmp/demo/houmao-server-dual-shadow-watch/autotest/case-interactive-shadow-validation
```

Canonical procedure:

1. Start the demo directly:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh start --json
```

2. Attach to all three tmux sessions:

- Claude: `tmux attach -t <claude-session>`
- Codex: `tmux attach -t <codex-session>`
- Monitor: `tmux attach -t <monitor-session>`

3. In each agent session, drive short prompts that exercise distinct states:

- submit a short question and watch `ready -> in_progress -> candidate_complete -> completed`
- trigger an operator-blocked interaction and watch `blocked`
- if the parser surface becomes unknown long enough, watch `unknown -> stalled`

4. Inspect the persisted evidence:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh inspect --json
```

5. Stop the run cleanly:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh stop --json
```

Optional staging helper:

```bash
scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh case-interactive-shadow-validation
```

That helper only stages the run and writes `result.json` with `"status": "ready_for_manual"`. The manual validation remains the primary procedure; it is not reduced to “just run the automatic script”.
