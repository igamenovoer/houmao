# Run Log: serverless james launch terminal handoff failure repeats

## Summary

Launching a fresh serverless Claude Code managed agent through `houmao-mgr` succeeded, but the post-launch terminal handoff still failed with `open terminal failed: not a terminal`.

## Environment

- Date: 2026-03-26 UTC
- Repo: `/data1/huangzhe/code/houmao`
- Agent definition root: `tests/fixtures/agents`
- Launch command:

```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents launch \
  --agents projection-demo \
  --provider claude_code \
  --agent-name james \
  --yolo
```

## Observed Output

```text
Managed agent launch complete:
agent_name=james
agent_id=b4cc344d25a2efe540adbf2678e2304c
tmux_session_name=AGENTSYS-james-1774526891442
manifest_path=/home/huangzhe/.houmao/runtime/sessions/local_interactive/local_interactive-20260326-120811Z-cf5e87a1/manifest.json
open terminal failed: not a terminal
```

## Notes

- Launch itself succeeded and the managed agent became available.
- `houmao-mgr agents state --agent-name james` reported `turn.phase: "ready"`.
- The failure remains limited to the terminal handoff path after a successful launch.
