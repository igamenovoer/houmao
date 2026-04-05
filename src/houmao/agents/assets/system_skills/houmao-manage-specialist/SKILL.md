---
name: houmao-manage-specialist
description: Use Houmao's supported project-easy specialist workflow to create, list, inspect, or remove reusable specialists with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Manage Specialist

Use this Houmao skill when you need to manage project-local easy specialists through `houmao-mgr project easy specialist ...` instead of hand-editing project files.

The trigger word `houmao` is intentional. Use the `houmao-manage-specialist` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these `project easy specialist` actions:

- `create`
- `list`
- `get`
- `remove`

This packaged skill does not cover:

- `houmao-mgr project easy instance launch`
- `houmao-mgr project easy instance list`
- `houmao-mgr project easy instance get`
- `houmao-mgr project easy instance stop`

## Workflow

1. Identify which specialist-management action the user wants: `create`, `list`, `get`, or `remove`.
2. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
3. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
4. Reuse that same resolved launcher for the selected specialist-management action.
5. Load exactly one action page:
   - `actions/create.md`
   - `actions/list.md`
   - `actions/get.md`
   - `actions/remove.md`
6. Follow the selected action page and report the result from the command that ran.

## Routing Guidance

- Use `actions/create.md` only when the user wants to create or replace a reusable specialist.
- Use `actions/list.md` only when the user wants to list persisted specialists.
- Use `actions/get.md` only when the user wants to inspect one persisted specialist definition.
- Use `actions/remove.md` only when the user wants to remove one persisted specialist definition.

## Guardrails

- Do not guess the intended action when the prompt could mean either specialist authoring or easy-instance runtime work.
- Do not route `project easy instance ...` tasks through this skill.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for specialist management.
