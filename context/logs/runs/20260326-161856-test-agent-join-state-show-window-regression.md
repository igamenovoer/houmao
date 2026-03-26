# Run Log: joined `test-agent-join` still falls back to tmux window `agent` on `state/show`

## Summary

During a live retest after reapplying the joined-local-TUI window-metadata fix, joining tmux session `test-agent-join` as `tester2` succeeded, but the immediate follow-up `houmao-mgr agents state` and `houmao-mgr agents show` commands still probed tmux window `agent` instead of the real adopted window `claude`.

## Environment

- Date: 2026-03-26 UTC
- Repo: `/data1/huangzhe/code/houmao`
- tmux session: `test-agent-join`
- live provider surface: window `0`, pane `0`, window name `claude`
- joined agent name: `tester2`
- joined agent id: `2e9fcf8e3df4d415c96bcf288d5ca4ba`
- manifest: `/home/huangzhe/.houmao/runtime/sessions/local_interactive/joined-local_interactive-20260326-161812Z-b6325db8/manifest.json`

## Commands

```bash
pixi run houmao-mgr agents join --agent-name tester2
pixi run houmao-mgr agents state --agent-name tester2
pixi run houmao-mgr agents show --agent-name tester2
```

## Observed Behavior

The join command succeeded and reported:

```text
Managed agent join complete:
agent_name=tester2
agent_id=2e9fcf8e3df4d415c96bcf288d5ca4ba
provider=claude_code
backend=local_interactive
tmux_session_name=test-agent-join
manifest_path=/home/huangzhe/.houmao/runtime/sessions/local_interactive/joined-local_interactive-20260326-161812Z-b6325db8/manifest.json
```

The immediate `state` and `show` follow-ups both reported the same probe failure:

```text
No tmux panes matched window index `0` and window `agent` in `test-agent-join`.
```

The returned managed-agent identity also reported:

```text
tmux_window_name: "agent"
```

## Manifest Snapshot After Failure

The persisted manifest at the time of the failure contained:

- `tmux.primary_window_name = null`
- `interactive.tmux_window_name = null`
- `backend_state.tmux_window_name = null`
- `launch_plan.metadata.tmux_window_name = "claude"`
- `agent_launch_authority.session_origin = "joined_tmux"`

The tmux session environment did publish the new joined-session pointers:

- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_ID`
- `AGENTSYS_AGENT_DEF_DIR`
- `AGENTSYS_JOB_DIR`

## Interpretation

The real CLI path is still clobbering or ignoring the adopted window metadata after join. The persisted normalized tmux-window fields are `null`, while the joined launch metadata still contains the correct adopted window name `claude`. The local `state/show` path therefore still falls back to `agent` in live testing, despite the intended fix.
