# Run Log: `agents join` fresh-generation registry conflict on reused joined identity

## Summary

During a second live retest against tmux session `test-agent-join`, `houmao-mgr agents join --agent-name tester` failed before publish with a shared-registry ownership conflict. The current tmux session had no `AGENTSYS_*` env published, but `houmao-mgr agents list` still showed a fresh local record for `tester` pointing at an earlier temp debug manifest under `/tmp/join-debug-...`.

## Environment

- Date: 2026-03-26 UTC
- Repo: `/data1/huangzhe/code/houmao`
- tmux session: `test-agent-join`
- live provider surface: window `0`, pane `0`, window name `claude`
- requested agent name: `tester`
- conflicting existing agent id: `f5d1278e8109edd94e1e4197e04873b9`
- conflicting existing manifest: `/tmp/join-debug-ya9w0b_4/session/manifest.json`

## Failing Command

```bash
pixi run houmao-mgr agents join --agent-name tester
```

## Observed Failure

The join command failed with:

```text
click.exceptions.ClickException: Shared-registry ownership conflict for agent_id `f5d1278e8109edd94e1e4197e04873b9` before publish: fresh generation `cd3e6e1c-929e-4c01-aecb-52a330150488` already owns that logical identity, so generation `60714c62-e099-4875-9671-950486fdce0f` must stand down.
```

The traceback showed the failure path through:

- `houmao.srv_ctrl.commands.agents.core.join_agents_command()`
- `houmao.srv_ctrl.commands.runtime_artifacts.materialize_joined_launch()`
- `houmao.agents.realm_controller.registry_storage.publish_live_agent_record()`
- `houmao.agents.realm_controller.registry_storage._raise_if_conflicting_fresh_generation()`

## Follow-up Observation

Immediately before the failed retry:

- `tmux show-environment -t test-agent-join` showed no `AGENTSYS_*` variables
- the live target session still only contained the user-run Claude TUI in window `0`
- `pixi run houmao-mgr agents list` still reported `tester`
- that `tester` record pointed at a temp debug manifest rather than a stable runtime-root manifest

## Interpretation

The join path currently treats the earlier `tester` registry record as a still-fresh owner of that logical identity, even though the corresponding joined session envelope no longer appears to be anchored to the live tmux session through tmux env publication. Reusing the same joined agent name therefore fails closed with a registry conflict instead of offering a clearer stale-ownership recovery path.
