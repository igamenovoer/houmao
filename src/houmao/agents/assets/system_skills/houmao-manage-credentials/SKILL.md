---
name: houmao-manage-credentials
description: Use Houmao's supported project-local auth-bundle workflow to list, inspect, add, update, or remove credentials with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Manage Credentials

Use this Houmao skill when you need to manage project-local tool auth bundles through `houmao-mgr project agents tools <tool> auth ...` instead of hand-editing `.houmao/agents/tools/`.

The trigger word `houmao` is intentional. Use the `houmao-manage-credentials` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these `project agents tools <tool> auth` actions:

- `list`
- `get`
- `add`
- `set`
- `remove`

This packaged skill does not cover:

- `houmao-mgr project easy specialist ...`
- `houmao-mgr project easy instance ...`
- `houmao-mgr agents launch|join|list|stop|cleanup`
- `houmao-mgr project agents tools <tool> setups ...`
- `houmao-mgr project agents roles ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents cleanup mailbox`
- `houmao-mgr admin cleanup runtime ...`
- direct filesystem editing under `.houmao/agents/tools/`

## Workflow

1. Identify which credential-management action the user wants: `list`, `get`, `add`, `set`, or `remove`.
2. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
3. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
4. Reuse that same resolved launcher for the selected credential-management action.
5. Load exactly one action page:
   - `actions/list.md`
   - `actions/get.md`
   - `actions/add.md`
   - `actions/set.md`
   - `actions/remove.md`
6. Follow the selected action page and report the result from the command that ran.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the tool lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.

## Routing Guidance

- Use `actions/list.md` only when the user wants to list auth bundles for one supported tool.
- Use `actions/get.md` only when the user wants to inspect one auth bundle safely through redacted CLI output.
- Use `actions/add.md` only when the user wants to create one new auth bundle.
- Use `actions/set.md` only when the user wants to update one existing auth bundle.
- Use `actions/remove.md` only when the user wants to remove one existing auth bundle.

## Guardrails

- Do not guess the intended action when the prompt could mean specialist authoring, live-agent lifecycle work, or credential management.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not scan env vars, tool homes, home directories, or unrelated filesystem locations to infer missing auth inputs unless the user explicitly asks for that narrower inspection.
- Do not print raw secret values or raw auth-file contents when `auth get` already provides safe redacted inspection.
- Do not invent provider-neutral credential flags, unsupported clear flags, or file inputs that the selected tool's `auth` surface does not actually support.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for credential management.
