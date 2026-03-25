# Real-Agent Interrupt Recovery

This guide walks the interrupt-focused validation path on the tracked two-lane subset: `claude-tui` and `codex-headless`.

## Goal

Prove that interrupt requests go through the same transport-neutral managed-agent request route, that the pack preserves before/after history evidence, and that the selected lanes can still be inspected and stopped cleanly afterward.

## Steps

1. Pick a fresh output root.

```bash
export DEMO_OUTPUT_DIR=/tmp/houmao-server-agent-api-interrupt
rm -rf "$DEMO_OUTPUT_DIR"
```

2. Start the interrupt-focused subset.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh start \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  --lane claude-tui \
  --lane codex-headless
```

Expected:

- the owned `houmao-server` starts
- only `claude-tui` and `codex-headless` are provisioned

3. Inspect the newly launched lanes.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh inspect \
  --demo-output-dir "$DEMO_OUTPUT_DIR"
```

Look for:

- both lanes are listed under `/houmao/agents`
- `claude-tui` reports `detail.transport = "tui"`
- `codex-headless` reports `detail.transport = "headless"`

4. Submit the tracked interrupt prompt.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh prompt \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  --lane claude-tui \
  --lane codex-headless \
  --prompt-file scripts/demo/houmao-server-agent-api-demo-pack/inputs/interrupt_prompt.txt
```

Expected:

```text
Both lanes accept the prompt through POST /houmao/agents/{agent_ref}/requests.
```

5. Submit the interrupt request.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh interrupt \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  --lane claude-tui \
  --lane codex-headless
```

6. Re-inspect with the optional TUI dialog tail enabled.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh inspect \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  --lane claude-tui \
  --lane codex-headless \
  --with-dialog-tail 400
```

Look for:

- `lanes/claude-tui/interrupt-verification.json`
- `lanes/codex-headless/interrupt-verification.json`
- `history_before` and `history_after` in both files
- optional `dialog_tail` text for `claude-tui`

7. Stop the run explicitly.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh stop \
  --demo-output-dir "$DEMO_OUTPUT_DIR"
```

8. Review the preserved evidence.

Check:

- `$DEMO_OUTPUT_DIR/lanes/claude-tui/interrupt-verification.json`
- `$DEMO_OUTPUT_DIR/lanes/codex-headless/interrupt-verification.json`
- `$DEMO_OUTPUT_DIR/control/stop_result.json`
- `$DEMO_OUTPUT_DIR/logs/server/`
