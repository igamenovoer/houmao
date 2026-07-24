---
name: houmao-agent-instance
description: Use when a Houmao managed-agent instance must be launched, joined, listed, stopped, relaunched, cleaned up, or must inspect or mutate its definition-owned runtime variables, named mindsets, or private workspace through actor-scoped commands.
license: MIT
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Agent Instance

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before lifecycle routing.

- Admin branch: act for the human operator, require an explicit project or managed-agent target, and never substitute `agents self` for that target.
- Agent branch: require freshly verified self identity, use verified self for supported self lifecycle follow-up, and require an explicit peer target for cross-agent work.

Preserve the actor branch for the entire route. Joining a session follows the admin entrypoint's explicit adoption handoff and never rewrites this frame in place.

Use this Houmao skill when you need to create, adopt, list, stop, relaunch, or clean up live managed-agent instances through `houmao-mgr` instead of hand-editing runtime files. It also owns definition-deployed instance state: typed runtime variables, named mindset revisions and skill snapshots, and one optional private workspace with stable semantic directory mappings. Managed-agent birth is project-scoped through `project agents launch`; follow-up lifecycle and instance state are split across `agents global`, explicit-target `agents single`, and verified-self `agents self`.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-instance`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-instance help`, `help for houmao-agent-instance`, `usage for houmao-agent-instance`, `available functionality for houmao-agent-instance`, or what this skill can do, answer from this section before choosing a lifecycle action, command, action page, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me stop this agent", route to the matching workflow instead of stopping at generic help.

Purpose: manage live Houmao-managed agent instances and their definition-owned, per-instance runtime state through supported actor-scoped commands.

Available functionality:

- `launch` new managed-agent instances from roles, presets, launch dossiers, or specialists.
- `join` one already-running supported provider session.
- `list` current live managed agents from the lifecycle perspective.
- `stop`, `relaunch`, or `cleanup` selected managed-agent instances.
- `runtime-variables` for typed, revisioned per-instance values.
- `mindsets` for named question sets, current revisions, diffs, and atomic skill snapshots.
- `private-workspace` for manifest validation, semantic directory resolution, materialization, remapping, tracking posture, mindset projection, and safe cleanup.

Common starting prompts:

- `$houmao-shared-routines agent-instance help`
- `$houmao-shared-routines agent-instance list`
- `$houmao-shared-routines agent-instance launch from specialist <name>`
- `$houmao-shared-routines agent-instance stop <agent>`
- `$houmao-shared-routines as-agent agent-instance runtime-variables get <key>`
- `$houmao-shared-routines agent-instance mindsets set <agent> <name>`
- `$houmao-shared-routines agent-instance private-workspace doctor <agent>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-definition` for specialist-scoped project launch and stop entry points or reusable definition authoring.
- Use `houmao-shared-routines->houmao-agent-inspect` for generic read-only state, logs, artifacts, mailbox posture, or screen inspection.
- Use `houmao-shared-routines->houmao-agent-messaging` for prompt, interrupt, mailbox routing, or reset-context work.
- Use `houmao-shared-routines->houmao-agent-gateway` for gateway sidecar lifecycle and gateway-only control.

## Subcommands

This packaged skill covers these managed-agent instance lifecycle and state actions:

- `help` (read-only meta operation)
- `launch`
- `join`
- `list`
- `stop`
- `relaunch`
- `cleanup`
- `runtime-variables`
- `mindsets`
- `private-workspace`

State routes load exactly one command page:

| Subcommand | Route | Actor Scope |
| --- | --- | --- |
| `runtime-variables` | [commands/runtime-variables.md](commands/runtime-variables.md) | agent read-only verified self; admin explicit-target read and mutation |
| `mindsets` | [commands/mindsets.md](commands/mindsets.md) | agent read-only verified self; admin explicit-target read and mutation |
| `private-workspace` | [commands/private-workspace.md](commands/private-workspace.md) | agent read-only verified self; admin explicit-target inspection and mutation |

`houmao-shared-routines->houmao-agent-definition` also owns the specialist-scoped easy `launch` and `stop` entry points, but this skill remains the canonical follow-up lifecycle surface for broader live-agent management.

This packaged skill does not cover:

- `houmao-mgr project specialist create`
- `houmao-mgr project specialist list`
- `houmao-mgr project specialist get`
- `houmao-mgr project specialist remove`
- `houmao-mgr project agents list`
- `houmao-mgr project agents get`
- `houmao-mgr project agents stop`
- generic managed-agent inspection of current state, logs, runtime artifacts, mailbox posture, or tmux backing
- `houmao-mgr agents single ... prompt` and `houmao-mgr agents self prompt`
- `houmao-mgr agents single ... interrupt` and `houmao-mgr agents self interrupt`
- `houmao-mgr agents single ... turn ...` and `houmao-mgr agents self turn ...`
- `houmao-mgr agents single ... gateway ...` and `houmao-mgr agents self gateway ...`
- `houmao-mgr agents single ... mailbox ...` and `houmao-mgr agents self mailbox ...`
- `houmao-mgr agents single ... mail ...` and `houmao-mgr agents self mail ...`
- destructive selected-agent cleanup under `houmao-mgr agents single ... cleanup ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr admin cleanup runtime ...`

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify which managed-agent lifecycle or state action the user wants: `launch`, `join`, `list`, `stop`, `relaunch`, `cleanup`, `runtime-variables`, `mindsets`, or `private-workspace`.
2. If the selected route is a state action, preserve the actor gate and load its one command page. An agent uses only verified-self read operations. An admin uses `agents single --agent-id|--agent-name ... instance-state` and may mutate only an explicit target.
3. If the requested action is `launch`, determine whether the source is:
   - a project profile for `houmao-mgr project agents launch --profile`, or
   - a predefined specialist for `houmao-mgr project agents launch --specialist`
4. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
5. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
6. Reuse that same chosen launcher for the selected instance-lifecycle or state action.
7. For supported command authoring, show and run direct maintained commands with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - `project agents launch` for project-scoped birth from a specialist or project profile
   - `agents self join`
   - `agents global list`
   - `agents single ... stop`
   - `agents single ... relaunch`
   - `agents single ... cleanup session`
   - `agents single ... cleanup logs`
   - `agents self instance-state ...` for verified-self state reads
   - `agents single --agent-id|--agent-name ... instance-state ...` for explicit-target admin state reads or mutation
8. If required input is missing or explicit inputs conflict, stop and recover the missing or conflicting input before running the target command.
9. Do not add optional posture, chat-session, cleanup, gateway, workspace, or mutation flags unless the user explicitly requested them or the selected tool/lane requires them.
10. Load exactly one action page:
   - `commands/launch.md`
   - `commands/join.md`
   - `commands/list.md`
   - `commands/stop.md`
   - `commands/relaunch.md`
   - `commands/cleanup.md`
   - `commands/runtime-variables.md`
   - `commands/mindsets.md`
   - `commands/private-workspace.md`
11. Follow the selected action page and report the result from the command that ran.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected lifecycle command, such as action, launch source lane, role/preset/launch-dossier/specialist name, instance name, join target, live-agent selector, cleanup kind, or cleanup selector
  - `Optional`: launcher preference, gateway or mailbox launch posture, headless provider args, output format, cleanup modifiers, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.
- DO NOT use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `commands/launch.md` only when the user wants to create one new managed-agent instance from a predefined role, preset, launch dossier, or specialist.
- Use `commands/join.md` only when the user wants Houmao to adopt one already-running supported provider session.
- Use `commands/list.md` only when the user wants the lifecycle-oriented list of current live managed agents. For generic read-only inspection of one agent, use `houmao-shared-routines->houmao-agent-inspect`.
- Use `commands/stop.md` only when the user wants to stop one live managed agent.
- Use `commands/relaunch.md` only when the user wants to relaunch one tmux-backed managed-agent surface without rebuilding the managed-agent home.
- Use `commands/cleanup.md` only when the user wants to remove stopped-session envelope artifacts or session-local logs.
- Use `commands/runtime-variables.md` for definition-declared typed values. Skills that consume live values must read them at use time instead of treating launch-time prompt snapshots as current.
- Use `commands/mindsets.md` for definition-declared named question sets. A required skill must take one atomic mindset snapshot before substantive work and stop if the snapshot fails.
- Use `commands/private-workspace.md` for one definition-owned individual workspace. Keep it distinct from multi-agent workspace topology under `houmao-utils-workspace-mgr`.
- Treat this skill as the canonical follow-up lifecycle surface after any specialist-scoped `launch` or `stop` handled through `houmao-shared-routines->houmao-agent-definition`.

## Guardrails

- DO NOT guess the intended action when the prompt could mean either specialist authoring or live instance lifecycle.
- DO NOT guess required action inputs that remain missing after checking the prompt and recent chat context.
- DO NOT route `project specialist ...` tasks through this skill.
- DO NOT present this skill as the canonical owner of generic managed-agent inspection; use `houmao-shared-routines->houmao-agent-inspect` for that read-only work.
- DO NOT route manual mailbox-enabled launch flags, mailbox cleanup, or mailbox registration tasks through this skill.
- DO NOT reject launch-dossier-backed launch just because the stored profile already carries gateway or mailbox defaults.
- DO NOT route project-aware instance `list|get|stop` through this skill; use the canonical `agents` lifecycle surface once the instance exists.
- DO NOT let an agent mutate its own runtime variables, mindset definitions, workspace mappings, tracking posture, or workspace contents through the read-only self surface.
- DO NOT use admin `agents self` state commands; require an explicit `agents single --agent-id|--agent-name` target.
- DO NOT read a live runtime variable from a stale launch-time prompt when the consuming skill contract requires the current value.
- DO NOT continue a required mindset-backed skill when the atomic snapshot fails.
- DO NOT hand-edit the private workspace TOML manifest or SQLite index.
- DO NOT silently replace `agents single ... relaunch` or `agents self relaunch` with a fresh launch command when relaunch authority or relaunch posture is unavailable.
- DO NOT skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- DO NOT probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- DO NOT use deprecated `houmao-cli` or removed standalone CAO launcher workflows for managed-agent lifecycle work.
