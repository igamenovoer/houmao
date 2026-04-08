---
name: houmao-manage-specialist
description: Use Houmao's supported project-easy workflow to create, list, inspect, or remove specialists and easy profiles, and to launch or stop easy instances from either source with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Manage Specialist

Use this Houmao skill when you need to manage project-local easy specialists, reusable easy profiles, and their easy-instance launch or stop flows through `houmao-mgr` instead of hand-editing project files.

The trigger word `houmao` is intentional. Use the `houmao-manage-specialist` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these routed easy-workflow actions:

- `create specialist`
- `create profile`
- `list specialists`
- `list profiles`
- `get specialist`
- `get profile`
- `remove specialist`
- `remove profile`
- `launch`
- `stop`

This packaged skill does not cover:

- `houmao-mgr project easy instance list`
- `houmao-mgr project easy instance get`
- generic managed-agent lifecycle beyond easy-workflow `launch` and `stop`

## Workflow

1. Identify which easy-workflow action the user wants: `create`, `list`, `get`, `remove`, `launch`, or `stop`, and whether it targets a `specialist`, a `profile`, or one easy instance.
2. If the requested action or target resource kind is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
3. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
4. Reuse that same chosen launcher for the selected easy-workflow action.
5. Load exactly one action page:
   - `actions/create.md`
   - `actions/list.md`
   - `actions/get.md`
   - `actions/remove.md`
   - `actions/launch.md`
   - `actions/stop.md`
6. Follow the selected action page and report the result from the command that ran.
7. After an easy-instance `launch` or `stop`, tell the user that further agent management should go through `houmao-manage-agent-instance`.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when several required fields or credential-lane choices need clarification
- Name the command you intend to run and keep the question scoped to the selected easy-workflow action and target resource kind.

## Routing Guidance

- Use `actions/create.md` only when the user wants to create or replace one reusable specialist or one reusable easy profile.
- Use `actions/list.md` only when the user wants to list persisted specialists or persisted easy profiles.
- Use `actions/get.md` only when the user wants to inspect one persisted specialist definition or one persisted easy profile.
- Use `actions/remove.md` only when the user wants to remove one persisted specialist definition or one persisted easy profile.
- Use `actions/launch.md` only when the user wants to launch one easy instance from an existing specialist or an existing easy profile.
- Use `actions/stop.md` only when the user wants to stop one easy instance in the easy workflow.

## Guardrails

- Do not guess the intended action when the prompt could mean specialist authoring, easy-profile authoring, or easy-instance runtime work.
- Do not guess between specialist and easy-profile authoring when the prompt could mean either reusable source.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route `project easy instance list|get` through this skill.
- Do not route generic managed-agent `join`, `list`, `stop`, or `cleanup` requests through this skill.
- Do not imply that this skill replaces `houmao-manage-agent-instance` for broader live-agent lifecycle work.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for specialist management.
