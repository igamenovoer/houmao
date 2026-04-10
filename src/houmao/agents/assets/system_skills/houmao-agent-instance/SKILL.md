---
name: houmao-agent-instance
description: Use Houmao's supported managed-agent lifecycle commands to launch, join, list, stop, relaunch, or clean up live agent instances created from predefined roles, presets, explicit launch profiles, or specialists.
license: MIT
---

# Houmao Agent Instance

Use this Houmao skill when you need to create, adopt, list, stop, relaunch, or clean up live managed-agent instances through `houmao-mgr` instead of hand-editing runtime files. This is the canonical Houmao-owned skill for general live-agent lifecycle work after any specialist-scoped launch or stop entry.

The trigger word `houmao` is intentional. Use the `houmao-agent-instance` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these managed-agent instance lifecycle actions:

- `launch`
- `join`
- `list`
- `stop`
- `relaunch`
- `cleanup`

`houmao-specialist-mgr` may also front specialist-scoped `launch` and `stop`, but this skill remains the canonical follow-up lifecycle surface for broader live-agent management.

This packaged skill does not cover:

- `houmao-mgr project easy specialist create`
- `houmao-mgr project easy specialist list`
- `houmao-mgr project easy specialist get`
- `houmao-mgr project easy specialist remove`
- `houmao-mgr project easy instance list`
- `houmao-mgr project easy instance get`
- `houmao-mgr project easy instance stop`
- generic managed-agent inspection of current state, logs, runtime artifacts, mailbox posture, or tmux backing
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents turn ...`
- `houmao-mgr agents gateway ...`
- `houmao-mgr agents mailbox ...`
- `houmao-mgr agents mail ...`
- `houmao-mgr agents cleanup mailbox`
- `houmao-mgr project mailbox ...`
- `houmao-mgr admin cleanup runtime ...`

## Workflow

1. Identify which managed-agent lifecycle action the user wants: `launch`, `join`, `list`, `stop`, `relaunch`, or `cleanup`.
2. If the requested action is `launch`, determine whether the source is:
   - a predefined role or preset for `houmao-mgr agents launch --agents`, or
   - an explicit project launch profile for `houmao-mgr agents launch --launch-profile`, or
   - a predefined specialist for `houmao-mgr project easy instance launch`
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected instance-lifecycle action.
6. Load exactly one action page:
   - `actions/launch.md`
   - `actions/join.md`
   - `actions/list.md`
   - `actions/stop.md`
   - `actions/relaunch.md`
   - `actions/cleanup.md`
7. Follow the selected action page and report the result from the command that ran.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.

## Routing Guidance

- Use `actions/launch.md` only when the user wants to create one new managed-agent instance from a predefined role, preset, explicit launch profile, or specialist.
- Use `actions/join.md` only when the user wants Houmao to adopt one already-running supported provider session.
- Use `actions/list.md` only when the user wants the lifecycle-oriented list of current live managed agents. For generic read-only inspection of one agent, use `houmao-agent-inspect`.
- Use `actions/stop.md` only when the user wants to stop one live managed agent.
- Use `actions/relaunch.md` only when the user wants to relaunch one tmux-backed managed-agent surface without rebuilding the managed-agent home.
- Use `actions/cleanup.md` only when the user wants to remove stopped-session envelope artifacts or session-local logs.
- Treat this skill as the canonical follow-up lifecycle surface after any specialist-scoped `launch` or `stop` handled through `houmao-specialist-mgr`.

## Guardrails

- Do not guess the intended action when the prompt could mean either specialist authoring or live instance lifecycle.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not route `project easy specialist ...` tasks through this skill.
- Do not present this skill as the canonical owner of generic managed-agent inspection; use `houmao-agent-inspect` for that read-only work.
- Do not route manual mailbox-enabled launch flags, mailbox cleanup, or mailbox registration tasks through this skill.
- Do not reject explicit launch-profile-backed launch just because the stored profile already carries gateway or mailbox defaults.
- Do not route project-aware instance `list|get|stop` through this skill; use the canonical `agents` lifecycle surface once the instance exists.
- Do not silently replace `agents relaunch` with a fresh launch command when relaunch authority or relaunch posture is unavailable.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for managed-agent lifecycle work.
