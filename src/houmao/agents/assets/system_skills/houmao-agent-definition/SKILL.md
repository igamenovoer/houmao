---
name: houmao-agent-definition
description: Use Houmao's canonical pre-launch agent-definition skill through explicit subcommands for roles, recipes, launch-dossiers, specialists, profiles, create-agent-fast-forward, launch-agent, and stop-agent.
license: MIT
---

# Houmao Agent Definition

Use this Houmao skill when the task is about persisted pre-launch agent definitions: what a specialist is, which reusable project profile should launch it, and which native launch dossiers should be stored before runtime.

The trigger word `houmao` is intentional. Use the `houmao-agent-definition` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-agent-definition help`, `help for houmao-agent-definition`, `usage for houmao-agent-definition`, `available functionality for houmao-agent-definition`, or what this skill can do, answer from this section before choosing a subcommand, subskill, command, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me create a specialist", route to the matching workflow instead of stopping at generic help.

Purpose: manage persisted pre-launch agent definitions, reusable project profiles, native launch dossiers, and specialist-backed launch or stop entry points.

Available functionality:

- `roles`, `recipes`, and `launch-dossiers` for low-level reusable agent-definition material.
- `specialists` and `profiles` for project authoring.
- `create-agent-fast-forward` for one-pass specialist plus project profile preparation.
- `launch-agent` and `stop-agent` for specialist-scoped project managed-agent entry points.
- Explicit direct brain-build plumbing routes through `houmao-mgr internals native-agent brain build`.

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
| `roles` | [subskills/low-level/roles.md](subskills/low-level/roles.md) | `houmao-mgr internals native-agent roles ...` |
| `recipes` | [subskills/low-level/recipes.md](subskills/low-level/recipes.md) | `houmao-mgr internals native-agent recipes ...`; `presets` is a compatibility alias |
| `launch-dossiers` | [subskills/low-level/launch-dossiers.md](subskills/low-level/launch-dossiers.md) | `houmao-mgr internals native-agent launch-dossiers ...` |
| `specialists` | [subskills/easy/specialists.md](subskills/easy/specialists.md) | `houmao-mgr project specialist ...` |
| `profiles` | [subskills/easy/profiles.md](subskills/easy/profiles.md) | `houmao-mgr project profile ...` |
| `create-agent-fast-forward` | [subskills/easy/create-agent-fast-forward.md](subskills/easy/create-agent-fast-forward.md) | specialist -> project profile -> launch command; does not launch |
| `launch-agent` | [subskills/easy/launch-instance.md](subskills/easy/launch-instance.md) | `houmao-mgr project agents launch`, then hand off broader live lifecycle to `houmao-agent-instance` |
| `stop-agent` | [subskills/easy/stop-instance.md](subskills/easy/stop-instance.md) | `houmao-mgr project agents stop`, then hand off broader live lifecycle to `houmao-agent-instance` |

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
   - launch dossier or exact `internals native-agent launch-dossiers` work -> `launch-dossiers`
   - specialist template work -> `specialists`
   - profile, agent profile, project profile, or ready profile work without native launch-dossier context -> `profiles`
   - one-pass specialist plus project profile preparation -> `create-agent-fast-forward`
   - project launch -> `launch-agent`
   - project stop -> `stop-agent`
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
7. For supported config-document authoring flows, generate the CLI-owned config draft before deciding the final maintained command. Config drafts are minimal opinionated drafts: they expose only required holes and fixed draft-owned values, not the full project subcommand option surface.
   - `project.specialist`
   - `project.profile`
   - `internals.native-agent.launch-dossier`
8. Generate config drafts only with the required fields for the selected draft id. The JSON intent must be an object with a top-level `fields` mapping; do not pass flat top-level draft fields.
   - `project.specialist`: `{"fields":{"name":"general-kimi","tool":"claude","credential":"kimi-coding"}}`
   - `project.profile`: `{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}`
   - `internals.native-agent.launch-dossier`: `{"fields":{"name":"reviewer-native","recipe":"reviewer-codex","credential":"reviewer-creds"}}`
   - `<chosen houmao-mgr launcher> internals config-drafts generate --id <draft-id> --intent '{"fields":{...}}'`
9. For full customization beyond those required holes, use the maintained project subcommands directly; do not pass hidden full-model fields such as model, env, mailbox, memo seed, gateway, prompt overlay, or credential material to config drafts.
10. For command-oriented flows that are not config documents, show and run direct maintained commands in fenced `bash` blocks, using only explicit user inputs and recovered explicit context:
   - `project agents launch`
   - `internals native-agent roles init|set`
   - `internals native-agent recipes add|set`
   - `internals native-agent brain build` when the user explicitly asks for direct native-agent brain-build plumbing
11. If draft generation reports blockers, or if a direct command would be missing required input or include conflicting explicit inputs, stop and recover the missing or conflicting input before running the target command.
12. Run maintained project commands only after all required inputs are explicit.
13. Report command output and any durable identity facts that affect later launch.

## Routing Rules

- Use `profiles` as the default meaning of `profile`, `agent profile`, `project profile`, and `ready profile`.
- Use `launch-dossiers` only when the user explicitly says `launch-dossiers`, launch dossier, or `internals native-agent launch-dossiers`.
- Use `create-agent-fast-forward` when the user wants the skill to create or select a specialist and then create or update the project profile in one pass.
- Use `launch-agent` and `stop-agent` only for project entry points, then hand off broad live-agent lifecycle to `houmao-agent-instance`.

## Guardrails

- Do not guess between low-level and easy lanes.
- Do not route loosely stated profile requests to launch dossiers by default.
- Do not guess between `profiles` and `launch-dossiers` when the user gives contradictory wording.
- Do not remove and recreate a role, recipe, specialist, or profile for ordinary patch edits when a maintained `set` command exists.
- Do not mutate credential bundle contents through this skill; route secret and auth-file edits to `houmao-credential-mgr`.
- Do not hand-author covered specialist/profile/launch-dossier config documents from Markdown skeletons when `houmao-mgr internals config-drafts generate` supports the surface.
- Do not preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled project launch; profile defaults or launch-time project bootstrap can own that common case.
- Do not use retired `houmao-mgr internals native-agent roles scaffold`.
- Do not use retired `houmao-mgr internals native-agent roles presets ...`.
- Do not use the retired top-level brain-build command; direct build plumbing is `houmao-mgr internals native-agent brain build`.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows.
