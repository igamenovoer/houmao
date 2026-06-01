---
name: houmao-agent-definition
description: Use Houmao's canonical pre-launch agent-definition skill through explicit subcommands for roles, recipes, raw-profiles, specialists, profiles, create-agent-fast-forward, launch-agent, and stop-agent.
license: MIT
---

# Houmao Agent Definition

Use this Houmao skill when the task is about persisted pre-launch agent definitions: what an agent is, which reusable profile should launch it, and which launch defaults should be stored before runtime.

The trigger word `houmao` is intentional. Use the `houmao-agent-definition` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-agent-definition help`, `help for houmao-agent-definition`, `usage for houmao-agent-definition`, `available functionality for houmao-agent-definition`, or what this skill can do, answer from this section before choosing a subcommand, subskill, command, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me create a specialist", route to the matching workflow instead of stopping at generic help.

Purpose: manage persisted pre-launch agent definitions, reusable profiles, and specialist-backed launch or stop entry points.

Available functionality:

- `roles`, `recipes`, and `raw-profiles` for low-level reusable agent-definition material.
- `specialists` and `profiles` for project-easy authoring.
- `create-agent-fast-forward` for one-pass specialist plus easy profile preparation.
- `launch-agent` and `stop-agent` for specialist-scoped easy instance entry points.

Common starting prompts:

- `$houmao-agent-definition help`
- `$houmao-agent-definition specialists list`
- `$houmao-agent-definition profiles create`
- `$houmao-agent-definition create-agent-fast-forward`

Related skills and boundaries:

- Use `houmao-credential-mgr` for credential bundle contents.
- Use `houmao-mailbox-mgr` for mailbox root or account administration.
- Use `houmao-utils-workspace-mgr` for workspace preparation.
- Use `houmao-agent-instance` for broad live managed-agent lifecycle after launch.

## Scope

This skill is the canonical router for these subcommands:

| Subcommand | Route | Underlying surface |
|---|---|---|
| `help` | this top-level `## Help` section | read-only meta operation; no `houmao-mgr` command |
| `roles` | [subskills/low-level/roles.md](subskills/low-level/roles.md) | `houmao-mgr project agents roles ...` |
| `recipes` | [subskills/low-level/recipes.md](subskills/low-level/recipes.md) | `houmao-mgr project agents recipes ...`; `presets` is a compatibility alias |
| `raw-profiles` | [subskills/low-level/raw-profiles.md](subskills/low-level/raw-profiles.md) | `houmao-mgr project agents launch-profiles ...` |
| `specialists` | [subskills/easy/specialists.md](subskills/easy/specialists.md) | `houmao-mgr project easy specialist ...` |
| `profiles` | [subskills/easy/profiles.md](subskills/easy/profiles.md) | `houmao-mgr project easy profile ...` |
| `create-agent-fast-forward` | [subskills/easy/create-agent-fast-forward.md](subskills/easy/create-agent-fast-forward.md) | specialist -> easy profile -> launch command; does not launch |
| `launch-agent` | [subskills/easy/launch-instance.md](subskills/easy/launch-instance.md) | `houmao-mgr project easy instance launch`, then hand off broader live lifecycle to `houmao-agent-instance` |
| `stop-agent` | [subskills/easy/stop-instance.md](subskills/easy/stop-instance.md) | `houmao-mgr project easy instance stop`, then hand off broader live lifecycle to `houmao-agent-instance` |

This skill does not own:

- credential bundle CRUD or secret mutation: use `houmao-credential-mgr`
- mailbox root/account administration: use `houmao-mailbox-mgr`
- workspace creation: use `houmao-utils-workspace-mgr`
- broad live managed-agent lifecycle after launch: use `houmao-agent-instance`
- direct hand-editing under `.houmao/`

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. If the user names a subcommand, route directly to that subcommand.
2. If no subcommand is named, infer the subcommand from intent:
   - role work -> `roles`
   - recipe or preset work -> `recipes`
   - raw profile, recipe-backed profile, or exact `project agents launch-profiles` work -> `raw-profiles`
   - specialist template work -> `specialists`
   - profile, agent profile, launch profile, or ready profile work without raw/recipe-backed context -> `profiles`
   - one-pass specialist plus easy profile preparation -> `create-agent-fast-forward`
   - easy launch -> `launch-agent`
   - easy stop -> `stop-agent`
3. Ask only when the prompt is still ambiguous after applying the routing rules.
4. Read the shared pages needed by that subcommand:
   - [subskills/common/launcher.md](subskills/common/launcher.md)
   - [subskills/common/missing-inputs.md](subskills/common/missing-inputs.md)
   - [subskills/common/profile-lanes.md](subskills/common/profile-lanes.md) when a profile lane is involved
   - [subskills/common/credential-routing.md](subskills/common/credential-routing.md) when credentials or auth names are involved
5. Load exactly one route subskill from the subcommand table.
6. Resolve one `houmao-mgr` launcher and reuse it for the turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if those do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request
7. For supported command-authoring flows, inspect and render the CLI-owned template before executing:
   - `project.easy.specialist.create|set`
   - `project.easy.profile.create|set`
   - `project.easy.instance.launch`
   - `project.agents.roles.init|set`
   - `project.agents.recipes.add|set`
   - `project.agents.launch-profiles.add|set`
8. Render sparse intent with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - `<chosen houmao-mgr launcher> --print-json internals command-templates show --id <template-id>`
   - `<chosen houmao-mgr launcher> --print-json internals command-templates render --id <template-id> --intent '<json>'`
9. If render output has blockers, stop and recover the missing or conflicting input before running the target command.
10. Run the rendered `argv` only after all required inputs are explicit.
11. Report command output and any durable identity facts that affect later launch.

## Routing Rules

- Use `profiles` as the default meaning of `profile`, `agent profile`, `launch profile`, and `ready profile`.
- Use `raw-profiles` only when the user explicitly says `raw-profiles`, raw profile, recipe-backed profile, or `project agents launch-profiles`.
- Use `create-agent-fast-forward` when the user wants the skill to create or select a specialist and then create or update the easy profile in one pass.
- Use `launch-agent` and `stop-agent` only for project-easy entry points, then hand off broad live-agent lifecycle to `houmao-agent-instance`.

## Guardrails

- Do not guess between low-level and easy lanes.
- Do not route loosely stated profile requests to raw profiles by default.
- Do not guess between `profiles` and `raw-profiles` when the user gives contradictory wording.
- Do not remove and recreate a role, recipe, specialist, or profile for ordinary patch edits when a maintained `set` command exists.
- Do not mutate credential bundle contents through this skill; route secret and auth-file edits to `houmao-credential-mgr`.
- Do not hand-author covered create, set, or launch commands from Markdown skeletons when `houmao-mgr internals command-templates render` supports the surface.
- Do not preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled easy launch; profile defaults or launch-time easy bootstrap can own that common case.
- Do not use retired `houmao-mgr project agents roles scaffold`.
- Do not use retired `houmao-mgr project agents roles presets ...`.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows.
