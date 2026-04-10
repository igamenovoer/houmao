---
name: houmao-agent-definition
description: Use Houmao's supported low-level project agent-definition commands to create, list, inspect, update, or remove roles and recipes with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Agent Definition

Use this Houmao skill when you need to manage project-local low-level agent definitions through `houmao-mgr project agents roles ...` and `houmao-mgr project agents recipes ...` instead of hand-editing `.houmao/agents/`.

The trigger word `houmao` is intentional. Use the `houmao-agent-definition` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these low-level definition actions:

- `create`
- `list`
- `get`
- `set`
- `remove`

This packaged skill routes those actions to the maintained low-level command families:

- `houmao-mgr project agents roles list|get|init|set|remove`
- `houmao-mgr project agents recipes list|get|add|set|remove`
- `houmao-mgr project agents presets list|get|add|set|remove` as the compatibility alias for the same recipe resources

This packaged skill does not cover:

- `houmao-mgr project easy specialist ...`
- `houmao-mgr project easy instance ...`
- `houmao-mgr agents launch|join|list|stop|cleanup`
- `houmao-mgr project credentials <tool> list|get|add|set|rename|remove` or `houmao-mgr credentials <tool> ... --agent-def-dir <path>` when the user wants credential management rather than which bundle one recipe references
- direct hand-editing under `.houmao/agents/`
- retired `houmao-mgr project agents roles scaffold`
- retired `houmao-mgr project agents roles presets ...`

## Workflow

1. Identify which definition-management action the user wants: `create`, `list`, `get`, `set`, or `remove`.
2. Determine whether the target is one low-level role or one named recipe.
3. If the action or target is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected definition-management action.
6. Load exactly one action page:
   - `actions/create.md`
   - `actions/list.md`
   - `actions/get.md`
   - `actions/set.md`
   - `actions/remove.md`
7. Follow the selected action page and report the result from the command that ran.
8. If the request is really about env vars or auth files inside an auth bundle, stop and route that work to `houmao-credential-mgr` instead of continuing inside this skill.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the target kind or several required fields need clarification
- Name the command you intend to run and keep the question scoped to the selected low-level action.

## Routing Guidance

- Use `actions/create.md` only when the user wants to create one new low-level role or one named recipe.
- Use `actions/list.md` only when the user wants to list low-level roles or named recipes.
- Use `actions/get.md` only when the user wants to inspect one low-level role or one named recipe. Add `--include-prompt` only when the user explicitly asked for prompt text or the full low-level role definition.
- Use `actions/set.md` only when the user wants to update one existing low-level role or one named recipe. Keep recipe auth-reference changes on `project agents recipes set --auth ...` or `--clear-auth`.
- Use `actions/remove.md` only when the user wants to remove one low-level role or one named recipe.

## Guardrails

- Do not guess the intended action when the prompt could mean easy specialist authoring, managed-agent lifecycle work, low-level definition management, or credential-bundle mutation.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route auth-bundle content mutation through this skill; use `houmao-credential-mgr`.
- Do not use `houmao-mgr project agents roles scaffold`.
- Do not use `houmao-mgr project agents roles presets ...`.
- Do not hand-edit `.houmao/agents/roles/`, `.houmao/agents/presets/`, `.houmao/agents/launch-profiles/`, or `.houmao/agents/tools/`.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for low-level definition management.
