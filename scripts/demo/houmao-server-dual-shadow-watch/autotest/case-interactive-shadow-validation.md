# Case: Interactive Prompt-and-Observe

Purpose: run the real operator journey against a demo-started `houmao-server`, interactively prompt both live TUIs, and observe how server-tracked state changes in the monitor.

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

3. In each agent session, drive short prompts that exercise distinct states and keep the turns easy to watch in the monitor:

- submit a short question and watch the server-tracked state move through `ready -> in_progress -> candidate_complete -> completed`
- trigger an operator-blocked interaction and watch the server report `blocked`
- if the parser surface becomes unknown long enough, watch the server report `unknown -> stalled`
- when the prompt looks quiet again, compare visible stability in the monitor with completion debounce timing instead of treating them as the same signal
- keep the monitor header in view so you can distinguish `monitor: poll=...` from `server posture: completion_debounce=... unknown->stalled=...`

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

That helper only stages the run and writes `result.json` with `"status": "ready_for_manual"`. The manual prompt-and-observe workflow remains the primary procedure; it is not reduced to “just run the automatic script”.
The case identifier stays `case-interactive-shadow-validation` for automation compatibility even though the operator workflow is now described as prompt-and-observe.
