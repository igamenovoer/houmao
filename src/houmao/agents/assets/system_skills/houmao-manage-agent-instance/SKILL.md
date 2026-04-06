---
name: houmao-manage-agent-instance
description: Use Houmao's supported managed-agent lifecycle commands to launch, join, list, stop, or clean up live agent instances created from predefined roles, presets, or specialists.
license: MIT
---

# Houmao Manage Agent Instance

Use this Houmao skill when you need to create, adopt, inspect, stop, or clean up live managed-agent instances through `houmao-mgr` instead of hand-editing runtime files.

The trigger word `houmao` is intentional. Use the `houmao-manage-agent-instance` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these managed-agent instance lifecycle actions:

- `launch`
- `join`
- `list`
- `stop`
- `cleanup`

This packaged skill does not cover:

- `houmao-mgr project easy specialist create`
- `houmao-mgr project easy specialist list`
- `houmao-mgr project easy specialist get`
- `houmao-mgr project easy specialist remove`
- `houmao-mgr project easy instance list`
- `houmao-mgr project easy instance get`
- `houmao-mgr project easy instance stop`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents relaunch`
- `houmao-mgr agents turn ...`
- `houmao-mgr agents gateway ...`
- `houmao-mgr agents mailbox ...`
- `houmao-mgr agents mail ...`
- `houmao-mgr agents cleanup mailbox`
- `houmao-mgr project mailbox ...`
- `houmao-mgr admin cleanup runtime ...`

## Workflow

1. Identify which managed-agent lifecycle action the user wants: `launch`, `join`, `list`, `stop`, or `cleanup`.
2. If the requested action is `launch`, determine whether the source is:
   - a predefined role or preset for `houmao-mgr agents launch`, or
   - a predefined specialist for `houmao-mgr project easy instance launch`
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
5. Reuse that same resolved launcher for the selected instance-lifecycle action.
6. Load exactly one action page:
   - `actions/launch.md`
   - `actions/join.md`
   - `actions/list.md`
   - `actions/stop.md`
   - `actions/cleanup.md`
7. Follow the selected action page and report the result from the command that ran.

## Routing Guidance

- Use `actions/launch.md` only when the user wants to create one new managed-agent instance from a predefined role, preset, or specialist.
- Use `actions/join.md` only when the user wants Houmao to adopt one already-running supported provider session.
- Use `actions/list.md` only when the user wants to list current live managed agents.
- Use `actions/stop.md` only when the user wants to stop one live managed agent.
- Use `actions/cleanup.md` only when the user wants to remove stopped-session envelope artifacts or session-local logs.

## Guardrails

- Do not guess the intended action when the prompt could mean either specialist authoring or live instance lifecycle.
- Do not route `project easy specialist ...` tasks through this skill.
- Do not route mailbox-enabled launch, mailbox cleanup, or mailbox registration tasks through this skill.
- Do not route project-aware instance `list|get|stop` through this skill; use the canonical `agents` lifecycle surface once the instance exists.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for managed-agent lifecycle work.
