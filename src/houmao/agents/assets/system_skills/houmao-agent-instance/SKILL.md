---
name: houmao-agent-instance
description: Use Houmao's supported managed-agent lifecycle commands to launch, join, list, stop, relaunch, or clean up live agent instances created from predefined roles, presets, launch dossiers, or specialists.
license: MIT
---

# Houmao Agent Instance

Use this Houmao skill when you need to create, adopt, list, stop, relaunch, or clean up live managed-agent instances through `houmao-mgr` instead of hand-editing runtime files. Managed-agent birth is project-scoped through `project agents launch`; follow-up lifecycle is split across `agents global`, `agents single`, and `agents self`.

The trigger word `houmao` is intentional. Use the `houmao-agent-instance` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-agent-instance help`, `help for houmao-agent-instance`, `usage for houmao-agent-instance`, `available functionality for houmao-agent-instance`, or what this skill can do, answer from this section before choosing a lifecycle action, command, action page, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me stop this agent", route to the matching workflow instead of stopping at generic help.

Purpose: manage live Houmao-managed agent instances through supported lifecycle commands.

Available functionality:

- `launch` new managed-agent instances from roles, presets, launch dossiers, or specialists.
- `join` one already-running supported provider session.
- `list` current live managed agents from the lifecycle perspective.
- `stop`, `relaunch`, or `cleanup` selected managed-agent instances.

Common starting prompts:

- `$houmao-agent-instance help`
- `$houmao-agent-instance list`
- `$houmao-agent-instance launch from specialist <name>`
- `$houmao-agent-instance stop <agent>`

Related skills and boundaries:

- Use `houmao-agent-definition` for specialist-scoped project launch and stop entry points or reusable definition authoring.
- Use `houmao-agent-inspect` for generic read-only state, logs, artifacts, mailbox posture, or screen inspection.
- Use `houmao-agent-messaging` for prompt, interrupt, mailbox routing, or reset-context work.
- Use `houmao-agent-gateway` for gateway sidecar lifecycle and gateway-only control.

## Scope

This packaged skill covers exactly these managed-agent instance lifecycle actions:

- `help` (read-only meta operation)
- `launch`
- `join`
- `list`
- `stop`
- `relaunch`
- `cleanup`

`houmao-agent-definition` also owns the specialist-scoped easy `launch` and `stop` entry points, but this skill remains the canonical follow-up lifecycle surface for broader live-agent management.

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

1. Identify which managed-agent lifecycle action the user wants: `launch`, `join`, `list`, `stop`, `relaunch`, or `cleanup`.
2. If the requested action is `launch`, determine whether the source is:
   - a project profile for `houmao-mgr project agents launch --profile`, or
   - a predefined specialist for `houmao-mgr project agents launch --specialist`
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected instance-lifecycle action.
6. For supported lifecycle command authoring, show and run direct maintained commands with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - `project agents launch` for project-scoped birth from a specialist or project profile
   - `agents join`
   - `agents global list`
   - `agents single ... stop`
   - `agents single ... relaunch`
   - `agents single ... cleanup session`
   - `agents single ... cleanup logs`
7. If required input is missing or explicit inputs conflict, stop and recover the missing or conflicting input before running the target command.
8. Do not add optional posture, chat-session, cleanup, or gateway flags unless the user explicitly requested them or the selected tool/lane requires them.
9. Load exactly one action page:
   - `actions/launch.md`
   - `actions/join.md`
   - `actions/list.md`
   - `actions/stop.md`
   - `actions/relaunch.md`
   - `actions/cleanup.md`
10. Follow the selected action page and report the result from the command that ran.

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
- Do not use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `actions/launch.md` only when the user wants to create one new managed-agent instance from a predefined role, preset, launch dossier, or specialist.
- Use `actions/join.md` only when the user wants Houmao to adopt one already-running supported provider session.
- Use `actions/list.md` only when the user wants the lifecycle-oriented list of current live managed agents. For generic read-only inspection of one agent, use `houmao-agent-inspect`.
- Use `actions/stop.md` only when the user wants to stop one live managed agent.
- Use `actions/relaunch.md` only when the user wants to relaunch one tmux-backed managed-agent surface without rebuilding the managed-agent home.
- Use `actions/cleanup.md` only when the user wants to remove stopped-session envelope artifacts or session-local logs.
- Treat this skill as the canonical follow-up lifecycle surface after any specialist-scoped `launch` or `stop` handled through `houmao-agent-definition`.

## Guardrails

- Do not guess the intended action when the prompt could mean either specialist authoring or live instance lifecycle.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route `project specialist ...` tasks through this skill.
- Do not present this skill as the canonical owner of generic managed-agent inspection; use `houmao-agent-inspect` for that read-only work.
- Do not route manual mailbox-enabled launch flags, mailbox cleanup, or mailbox registration tasks through this skill.
- Do not reject launch-dossier-backed launch just because the stored profile already carries gateway or mailbox defaults.
- Do not route project-aware instance `list|get|stop` through this skill; use the canonical `agents` lifecycle surface once the instance exists.
- Do not silently replace `agents single ... relaunch` or `agents self relaunch` with a fresh launch command when relaunch authority or relaunch posture is unavailable.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows for managed-agent lifecycle work.
