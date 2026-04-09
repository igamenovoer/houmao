---
name: houmao-project-mgr
description: Use Houmao's project-management skill for project overlay lifecycle, `.houmao/` layout, project-aware command effects, explicit launch profiles, and project-scoped easy-instance inspection or stop workflows.
license: MIT
---

# Houmao Project Manager

Use this Houmao skill when the task is about the Houmao project overlay itself: initializing it, explaining its layout, understanding how project context changes other commands, managing explicit launch profiles, or inspecting or stopping easy instances through the selected overlay.

The trigger word `houmao` is intentional. Use the `houmao-project-mgr` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these project-management surfaces:

- `houmao-mgr project init`
- `houmao-mgr project status`
- `houmao-mgr project agents launch-profiles ...`
- `houmao-mgr project easy instance list|get|stop`

This packaged skill does not cover:

- `houmao-mgr project easy specialist ...`
- `houmao-mgr project easy profile ...`
- `houmao-mgr project easy instance launch`
- `houmao-mgr project credentials <tool> ...`
- `houmao-mgr project agents roles ...`
- `houmao-mgr project agents recipes ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents launch|join|list|state|stop|relaunch|cleanup`
- direct hand-editing inside `.houmao/`

## Workflow

1. Identify whether the user wants project overlay lifecycle, project layout explanation, project-aware side effects, explicit launch-profile management, or project-scoped easy-instance inspection or stop.
2. When the task is explanatory rather than operational, load the narrowest reference page you need before deciding whether any command should run.
3. If the user really wants specialist/profile authoring, auth-bundle CRUD, low-level role/recipe editing, mailbox administration, or generic live-agent lifecycle, stop and route the request to the correct renamed Houmao skill before continuing.
4. Recover omitted inputs from the current prompt first and recent chat context second, but only when the user stated them explicitly.
5. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
6. Reuse that same chosen launcher for the selected project-management action.
7. Load exactly one action page when the task is operational, or the narrowest reference page when the task is explanatory.
8. Report the result from the command that ran and keep the renamed skill-routing boundaries explicit.

## Actions

- Read [actions/init.md](actions/init.md) to create or validate the selected project overlay.
- Read [actions/status.md](actions/status.md) to inspect which project overlay is selected and whether a stateful project-aware flow would bootstrap it.
- Read [actions/launch-profiles.md](actions/launch-profiles.md) to list, inspect, add, update, or remove explicit recipe-backed launch profiles.
- Read [actions/easy-instances.md](actions/easy-instances.md) to list, inspect, or stop easy instances through the selected project overlay.

## References

- Read [references/overlay-resolution.md](references/overlay-resolution.md) when project overlay discovery or env override behavior matters.
- Read [references/project-layout.md](references/project-layout.md) when the question is how files are organized under `.houmao/`.
- Read [references/project-aware-effects.md](references/project-aware-effects.md) when the question is what changes for other `houmao-mgr` command families once a project overlay exists.
- Read [references/routing-boundaries.md](references/routing-boundaries.md) when the task is close to a neighboring renamed Houmao skill and ownership needs to stay explicit.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the project-management lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.

## Routing Guidance

- Use `actions/init.md` only when the user wants to create or validate the selected project overlay.
- Use `actions/status.md` only when the user wants to inspect overlay selection, effective project-aware roots, or bootstrap posture.
- Use `actions/launch-profiles.md` only when the user wants to manage explicit recipe-backed launch profiles under `project agents launch-profiles ...`.
- Use `actions/easy-instances.md` only when the user wants `project easy instance list|get|stop` through the selected project overlay.
- Route easy specialist or easy profile authoring, and easy `launch|stop`, to `houmao-specialist-mgr`.
- Route project-local auth-bundle CRUD to `houmao-credential-mgr`.
- Route low-level roles and recipes to `houmao-agent-definition`.
- Route generic managed-agent lifecycle after project-scoped routing to `houmao-agent-instance`.
- Route mailbox administration to `houmao-mailbox-mgr`.

## Guardrails

- Do not guess whether the task is project explanation, launch-profile management, or project-scoped easy-instance inspection when the prompt is ambiguous.
- Do not treat `project easy instance launch` as part of this skill; that belongs to `houmao-specialist-mgr`.
- Do not treat project-scoped launch-profile `--auth` overrides as auth-bundle CRUD.
- Do not imply that `project easy instance list|get|stop` bootstrap a missing overlay automatically; they use non-creating selected-overlay resolution.
- Do not hand-edit `.houmao/` files when the maintained `houmao-mgr` surfaces already cover the task.
- Do not use obsolete `houmao-manage-*` identifiers as current routing targets.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for project management.
