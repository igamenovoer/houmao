---
name: houmao-manage-specialist
description: Use Houmao's supported project-easy specialist workflow to create, list, inspect, remove, launch, or stop specialist-backed easy instances with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Manage Specialist

Use this Houmao skill when you need to manage project-local easy specialists and their specialist-scoped launch or stop flows through `houmao-mgr` instead of hand-editing project files.

The trigger word `houmao` is intentional. Use the `houmao-manage-specialist` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these routed specialist workflow actions:

- `create`
- `list`
- `get`
- `remove`
- `launch`
- `stop`

This packaged skill does not cover:

- `houmao-mgr project easy instance list`
- `houmao-mgr project easy instance get`
- generic managed-agent lifecycle beyond specialist-scoped `launch` and `stop`

## Workflow

1. Identify which specialist workflow action the user wants: `create`, `list`, `get`, `remove`, `launch`, or `stop`.
2. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
3. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
4. Reuse that same resolved launcher for the selected specialist action.
5. Load exactly one action page:
   - `actions/create.md`
   - `actions/list.md`
   - `actions/get.md`
   - `actions/remove.md`
   - `actions/launch.md`
   - `actions/stop.md`
6. Follow the selected action page and report the result from the command that ran.
7. After a specialist-backed `launch` or `stop`, tell the user that further agent management should go through `houmao-manage-agent-instance`.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when several required fields or credential-lane choices need clarification
- Name the command you intend to run and keep the question scoped to the selected specialist action.

## Routing Guidance

- Use `actions/create.md` only when the user wants to create or replace a reusable specialist.
- Use `actions/list.md` only when the user wants to list persisted specialists.
- Use `actions/get.md` only when the user wants to inspect one persisted specialist definition.
- Use `actions/remove.md` only when the user wants to remove one persisted specialist definition.
- Use `actions/launch.md` only when the user wants to launch one easy instance from an existing specialist.
- Use `actions/stop.md` only when the user wants to stop one easy instance in the specialist workflow.

## Guardrails

- Do not guess the intended action when the prompt could mean either specialist authoring or easy-instance runtime work.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route `project easy instance list|get` through this skill.
- Do not route generic managed-agent `join`, `list`, `stop`, or `cleanup` requests through this skill.
- Do not imply that this skill replaces `houmao-manage-agent-instance` for broader live-agent lifecycle work.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for specialist management.
