---
name: houmao-manage-agent-definition
description: Use Houmao's supported low-level project agent-definition commands to create, list, inspect, update, or remove roles and presets with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Manage Agent Definition

Use this Houmao skill when you need to manage project-local low-level agent definitions through `houmao-mgr project agents roles ...` and `houmao-mgr project agents presets ...` instead of hand-editing `.houmao/agents/`.

The trigger word `houmao` is intentional. Use the `houmao-manage-agent-definition` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these low-level definition actions:

- `create`
- `list`
- `get`
- `set`
- `remove`

This packaged skill routes those actions to the maintained low-level command families:

- `houmao-mgr project agents roles list|get|init|set|remove`
- `houmao-mgr project agents presets list|get|add|set|remove`

This packaged skill does not cover:

- `houmao-mgr project easy specialist ...`
- `houmao-mgr project easy instance ...`
- `houmao-mgr agents launch|join|list|stop|cleanup`
- `houmao-mgr project agents tools <tool> auth list|get|add|set|remove` when the user wants to mutate auth-bundle contents rather than which bundle one preset references
- direct hand-editing under `.houmao/agents/`
- retired `houmao-mgr project agents roles scaffold`
- retired `houmao-mgr project agents roles presets ...`

## Workflow

1. Identify which definition-management action the user wants: `create`, `list`, `get`, `set`, or `remove`.
2. Determine whether the target is one low-level role or one named preset.
3. If the action or target is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
5. Reuse that same resolved launcher for the selected definition-management action.
6. Load exactly one action page:
   - `actions/create.md`
   - `actions/list.md`
   - `actions/get.md`
   - `actions/set.md`
   - `actions/remove.md`
7. Follow the selected action page and report the result from the command that ran.
8. If the request is really about env vars or auth files inside an auth bundle, stop and route that work to `houmao-manage-credentials` instead of continuing inside this skill.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the target kind or several required fields need clarification
- Name the command you intend to run and keep the question scoped to the selected low-level action.

## Routing Guidance

- Use `actions/create.md` only when the user wants to create one new low-level role or one named preset.
- Use `actions/list.md` only when the user wants to list low-level roles or named presets.
- Use `actions/get.md` only when the user wants to inspect one low-level role or one named preset. Add `--include-prompt` only when the user explicitly asked for prompt text or the full low-level role definition.
- Use `actions/set.md` only when the user wants to update one existing low-level role or one named preset. Keep preset auth-reference changes on `project agents presets set --auth ...` or `--clear-auth`.
- Use `actions/remove.md` only when the user wants to remove one low-level role or one named preset.

## Guardrails

- Do not guess the intended action when the prompt could mean easy specialist authoring, managed-agent lifecycle work, low-level definition management, or credential-bundle mutation.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route auth-bundle content mutation through this skill; use `houmao-manage-credentials`.
- Do not use `houmao-mgr project agents roles scaffold`.
- Do not use `houmao-mgr project agents roles presets ...`.
- Do not hand-edit `.houmao/agents/roles/`, `.houmao/agents/presets/`, or `.houmao/agents/tools/`.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for low-level definition management.
