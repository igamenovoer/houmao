# Run Log: `houmao-mgr agents state` transient `.claude.json` parse failure

## Summary

During a fresh serverless Claude Code managed-agent retest, `houmao-mgr agents state --agent-name james` failed once with a transient JSON parse error while resuming runtime state from the provider home. A later retry against the same session succeeded without intervention.

## Environment

- Date: 2026-03-26 UTC
- Repo: `/data1/huangzhe/code/houmao`
- Managed agent name: `james`
- tmux session: `AGENTSYS-james-1774526891442`
- Manifest: `/home/huangzhe/.houmao/runtime/sessions/local_interactive/local_interactive-20260326-120811Z-cf5e87a1/manifest.json`

## Failing Command

```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents state --agent-name james
```

## Observed Failure

The command raised:

```text
LaunchPlanError: Malformed JSON state `/home/huangzhe/.houmao/runtime/homes/claude-brain-20260326-120811Z-c96c65/.claude.json`: Expecting value (line 1, column 1).
```

The traceback showed the failure path through:

- `houmao.agents.launch_policy.provider_hooks.load_json_state()`
- `houmao.agents.launch_policy.provider_hooks.set_json_key()`
- `houmao.agents.realm_controller.launch_plan.build_launch_plan()`
- `houmao.srv_ctrl.commands.managed_agents._resume_controller_from_record()`

## Follow-up Observation

Immediately after the failure:

- the target `.claude.json` file existed
- the file was non-empty
- a later `houmao-mgr agents state --agent-name james` retry succeeded
- gateway attach and gateway prompt also succeeded for the same session

## Interpretation

This looks like a transient read-versus-write race on provider-owned JSON state rather than durable file corruption. The resume path appears to read `.claude.json` without tolerating a temporary partially-written file.
